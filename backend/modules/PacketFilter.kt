package com.sentinel.omega.core.vpn

import java.nio.ByteBuffer
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.TimeUnit

/**
 * Stateful Packet Filter implementing the Leaky Bucket algorithm.
 * 
 * FEATURES:
 * - Weighted Threat Scoring (Linear Accumulation).
 * - Monotonic Time Decay (Resilient to clock changes).
 * - Temporary Quarantine for abusive sources.
 * - Configurable Rules and Thresholds.
 */
object PacketFilter {

    // --- CONFIGURATION ---
    data class Config(
        val allowedPorts: Set<Int> = setOf(443, 80, 53, 8080),
        val quarantineThreshold: Int = 100,
        val decayIntervalNs: Long = TimeUnit.SECONDS.toNanos(60), // 60s in nanoseconds
        val decayAmount: Int = 10,
        val maxTrackedIps: Int = 10_000,
        val debugMode: Boolean = false // Enables verbose logging, does NOT bypass logic
    )

    private var config = Config()
    
    // Admin Allowlist (Injected at Runtime, intended for Debug builds only)
    private val allowedIps = ConcurrentHashMap.newKeySet<String>()

    /**
     * Initialize the filter with specific configuration.
     * Should be called during VPN service startup.
     */
    fun configure(newConfig: Config) {
        this.config = newConfig
    }

    /**
     * Add trusted IPs that bypass the filter.
     * CRITICAL: Ensure this is only called in DEBUG builds or strictly controlled environments.
     */
    fun setAllowlist(ips: List<String>) {
        if (!config.debugMode && ips.isNotEmpty()) {
             // Optional: Log warning about allowlist usage in non-debug mode
             // System.out.println("WARNING: Allowlist set in non-debug mode.")
        }
        allowedIps.clear()
        allowedIps.addAll(ips)
    }

    // --- STATE ---
    private data class ThreatState(
        var score: Int = 0,
        var lastSeenNs: Long = System.nanoTime(),
        var isQuarantined: Boolean = false
    )

    // Map<SourceIP, ThreatState>
    private val threatMap = ConcurrentHashMap<String, ThreatState>()

    // --- OBSERVABILITY ---
    val metrics = Metrics()

    class Metrics {
        val droppedPackets = AtomicLong(0)
        val bannedIps = AtomicLong(0)
        val dropsByReason = ConcurrentHashMap<String, AtomicLong>()
        val activeTrackingCount get() = PacketFilter.threatMap.size // Accessor via outer object
    }

    // --- PACKET PROCESSING ---

    data class PacketInfo(
        val srcIp: String,
        val dstIp: String,
        val protocol: Int,
        val srcPort: Int,
        val dstPort: Int,
        val version: Int
    )

    fun processPacket(buffer: ByteBuffer, length: Int): PacketInfo? {
        val nowNs = System.nanoTime()

        // 1. Sanity Check
        if (length < 20) {
            recordDrop("MALFORMED_HEADER")
            return null
        }

        try {
            // Basic IPv4 Parsing
            val version = (buffer.get(0).toInt() shr 4) and 0xF
            if (version != 4) return null 

            val headerLen = (buffer.get(0).toInt() and 0xF) * 4
            val protocol = buffer.get(9).toInt() and 0xFF
            val srcIp = ipv4ToString(buffer, 12)
            val dstIp = ipv4ToString(buffer, 16)

            // 2. Allowlist Check (Bypass)
            if (allowedIps.contains(srcIp)) {
                return parseDeep(buffer, headerLen, protocol, srcIp, dstIp, version, length)
            }

            // 3. Threat Assessment (Leaky Bucket)
            val state = threatMap.compute(srcIp) { _, currentState ->
                val s = currentState ?: ThreatState(lastSeenNs = nowNs)
                
                // Decay Logic (Score -= TimeDelta / Interval * Amount)
                val timeDeltaNs = nowNs - s.lastSeenNs
                if (timeDeltaNs > config.decayIntervalNs) {
                    val intervals = timeDeltaNs / config.decayIntervalNs
                    val reduction = (intervals * config.decayAmount).toInt()
                    
                    s.score = (s.score - reduction).coerceAtLeast(0)
                    
                    // Release Quarantine if below threshold
                    if (s.score < config.quarantineThreshold && s.isQuarantined) {
                        s.isQuarantined = false
                    }
                    // Reset lastSeen only if we applied decay, or just update it to now?
                    // Leaky bucket usually updates 'last leak time'.
                    // For this simple implementation, 'lastSeen' acts as 'last decay check' effectively on activity.
                }
                s.lastSeenNs = nowNs
                s
            }!!

            // Check Quarantine
            if (state.isQuarantined) {
                recordDrop("QUARANTINED")
                return null
            }

            // 4. Deep Inspection & Rule Application
            var riskWeight = 0
            val info = parseDeep(buffer, headerLen, protocol, srcIp, dstIp, version, length)

            if (info != null) {
                // Rule: Port Policy
                if (info.dstPort !in config.allowedPorts) {
                    riskWeight += 10 // Weight for policy violation
                }
            } else {
                riskWeight += 20 // Weight for malformed transport
            }

            // 5. Update Score
            if (riskWeight > 0) {
                synchronized(state) {
                    // Check for overflow protection (though Int.MAX_VALUE is high)
                    if (state.score < Int.MAX_VALUE - riskWeight) {
                        state.score += riskWeight
                    } else {
                        state.score = Int.MAX_VALUE
                    }
                    
                    // Trigger Quarantine
                    if (state.score >= config.quarantineThreshold && !state.isQuarantined) {
                        state.isQuarantined = true
                        metrics.bannedIps.incrementAndGet()
                        log("BAN_TRIGGERED for $srcIp (Score: ${state.score})")
                    }
                }
            }

            // Cleanup if malformed
            if (info == null) {
                recordDrop("MALFORMED_TRANSPORT")
                return null
            }

            return info

        } catch (e: Exception) {
            recordDrop("EXCEPTION_PARSE")
            return null
        }
    }

    // --- INTERNAL HELPERS ---

    private fun parseDeep(buffer: ByteBuffer, headerLen: Int, protocol: Int, srcIp: String, dstIp: String, version: Int, totalLen: Int): PacketInfo? {
        var srcPort = 0
        var dstPort = 0
        if (protocol == 6 || protocol == 17) { // TCP or UDP
            if (totalLen >= headerLen + 4) {
                srcPort = buffer.getShort(headerLen).toInt() and 0xFFFF
                dstPort = buffer.getShort(headerLen + 2).toInt() and 0xFFFF
            } else {
                return null
            }
        }
        return PacketInfo(srcIp, dstIp, protocol, srcPort, dstPort, version)
    }

    private fun recordDrop(reasonCode: String) {
        metrics.droppedPackets.incrementAndGet()
        metrics.dropsByReason.computeIfAbsent(reasonCode) { AtomicLong(0) }.incrementAndGet()
        
        if (config.debugMode) {
             log("DROP: $reasonCode")
        }
    }

    private fun log(msg: String) {
        // In Android, use Log.d/w. Here using System.out for scratching.
        if (config.debugMode) {
            System.out.println("[PacketFilter] $msg")
        }
    }

    private fun ipv4ToString(buf: ByteBuffer, offset: Int): String {
        return "${buf.get(offset).toInt() and 0xFF}." +
               "${buf.get(offset + 1).toInt() and 0xFF}." +
               "${buf.get(offset + 2).toInt() and 0xFF}." +
               "${buf.get(offset + 3).toInt() and 0xFF}"
    }

    /**
     * Maintenance Task.
     * Call periodically to remove stale entries.
     * Strategy: TTL Eviction, followed by Safety Cap Flush.
     */
    fun performMaintenance() {
        val nowNs = System.nanoTime()
        // TTL: 10x decay interval
        val expiryAgeNs = config.decayIntervalNs * 10 
        
        threatMap.entries.removeIf { (_, state) ->
            (nowNs - state.lastSeenNs) > expiryAgeNs
        }
        
        // Safety Cap: If still over limit, flush all (Fail-safe)
        // In a more complex implementation, we'd use LRU, but ConcurrentHashMap doesn't support it natively.
        if (threatMap.size > config.maxTrackedIps) {
             threatMap.clear() 
             log("EMERGENCY_FLUSH: Max IPs exceeded")
        }
    }
}
