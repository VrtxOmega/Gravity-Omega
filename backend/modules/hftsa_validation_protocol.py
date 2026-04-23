"""
HFT-SA NO-HARDWARE VALIDATION PROTOCOL
Binary test: Does turbulence-acoustic precursor exist?

OUTCOMES:
  PASS - Precursor exists, separable, early enough
  INCONCLUSIVE - Signal exists but not separable OR inconsistent
  FAIL - No precursor OR Δt < control loop response

NO "PROMISING" ALLOWED.
"""

import numpy as np
from scipy import signal
from scipy.fft import stft
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json
from datetime import datetime


@dataclass
class ThrottleEvent:
    """Thermal throttling event with timestamp"""
    timestamp: float  # seconds since epoch
    node_id: str
    temperature: float  # °C
    event_type: str  # "throttle_start", "throttle_end"


@dataclass
class AcousticData:
    """Time-series acoustic/vibration data"""
    timestamps: np.ndarray  # seconds since epoch
    signal: np.ndarray  # vibration/acoustic amplitude
    sampling_rate: float  # Hz
    sensor_location: str


@dataclass
class PrecursorCandidate:
    """Potential precursor signal"""
    event_timestamp: float
    precursor_timestamp: float
    lead_time: float  # seconds
    confidence: float  # 0-1
    spectral_features: dict


class ValidationProtocol:
    """
    No-hardware validation experiment.
    
    Rule: Binary outcomes only.
    """
    
    def __init__(self, 
                 min_lead_time: float = 2.0,  # seconds
                 consistency_threshold: float = 0.8,  # 80% of events
                 snr_threshold: float = 3.0):  # 10 dB
        
        self.min_lead_time = min_lead_time
        self.consistency_threshold = consistency_threshold
        self.snr_threshold = snr_threshold
        
        # Results
        self.precursors: List[PrecursorCandidate] = []
        self.missing_events: List[float] = []
        self.false_positives: List[float] = []
    
    def step1_align_timelines(self, 
                              acoustic: AcousticData, 
                              throttle_events: List[ThrottleEvent]) -> dict:
        """
        Step 1: Align acoustic data with throttle events.
        
        NO SMOOTHING. NO ML. Raw alignment only.
        """
        print("\n[STEP 1: TIMELINE ALIGNMENT]")
        print(f"Acoustic data: {len(acoustic.timestamps)} samples @ {acoustic.sampling_rate} Hz")
        print(f"Throttle events: {len(throttle_events)}")
        
        # Validate temporal overlap
        acoustic_start = acoustic.timestamps[0]
        acoustic_end = acoustic.timestamps[-1]
        
        valid_events = []
        for event in throttle_events:
            if acoustic_start <= event.timestamp <= acoustic_end:
                valid_events.append(event)
            else:
                print(f"  WARNING: Event at {event.timestamp} outside acoustic range")
        
        print(f"Valid events in acoustic window: {len(valid_events)}")
        
        return {
            'total_events': len(throttle_events),
            'valid_events': len(valid_events),
            'acoustic_duration': acoustic_end - acoustic_start,
            'events': valid_events
        }
    
    def step2_spectral_decomposition(self, 
                                     acoustic: AcousticData,
                                     window_size: int = 1024) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Step 2: STFT decomposition.
        
        Track:
        - Broadband energy shifts
        - Narrowband peak emergence
        - Spectral entropy changes
        """
        print("\n[STEP 2: SPECTRAL DECOMPOSITION]")
        
        # Short-Time Fourier Transform
        f, t, Zxx = stft(acoustic.signal, 
                         fs=acoustic.sampling_rate, 
                         nperseg=window_size)
        
        # Power spectral density
        Pxx = np.abs(Zxx) ** 2
        
        print(f"Frequency bins: {len(f)}")
        print(f"Time bins: {len(t)}")
        print(f"Frequency range: {f[0]:.1f} - {f[-1]:.1f} Hz")
        
        # Broadband energy (total power)
        broadband_energy = np.sum(Pxx, axis=0)
        
        # Spectral entropy (measure of disorder)
        # Higher entropy = more uniform spectrum (noise-like)
        # Lower entropy = concentrated spectrum (tonal)
        spectral_entropy = -np.sum(
            (Pxx / np.sum(Pxx, axis=0, keepdims=True)) * 
            np.log(Pxx / np.sum(Pxx, axis=0, keepdims=True) + 1e-10),
            axis=0
        )
        
        return f, t + acoustic.timestamps[0], (Pxx, broadband_energy, spectral_entropy)
    
    def step3_backward_correlation(self,
                                   event: ThrottleEvent,
                                   spectral_time: np.ndarray,
                                   spectral_features: Tuple[np.ndarray, np.ndarray, np.ndarray],
                                   lookback_window: float = 60.0) -> Optional[PrecursorCandidate]:
        """
        Step 3: For each throttle event, look backward for precursor.
        
        Hunt for:
        - Changes in turbulence signatures
        - Reynolds-correlated frequency shifts
        - Increasing variance/intermittency
        """
        Pxx, broadband_energy, spectral_entropy = spectral_features
        
        # Find time indices in lookback window
        lookback_start = event.timestamp - lookback_window
        lookback_indices = np.where((spectral_time >= lookback_start) & 
                                   (spectral_time < event.timestamp))[0]
        
        if len(lookback_indices) < 2:
            return None
        
        # Baseline (far from event)
        baseline_indices = lookback_indices[:len(lookback_indices)//3]
        baseline_energy = np.mean(broadband_energy[baseline_indices])
        baseline_entropy = np.mean(spectral_entropy[baseline_indices])
        
        # Search for deviation from baseline
        energy_threshold = baseline_energy * 1.5  # 50% increase
        entropy_threshold = baseline_entropy * 0.8  # 20% decrease (more tonal)
        
        # Find first crossing
        precursor_idx = None
        for idx in lookback_indices:
            if (broadband_energy[idx] > energy_threshold or 
                spectral_entropy[idx] < entropy_threshold):
                precursor_idx = idx
                break
        
        if precursor_idx is None:
            return None
        
        precursor_time = spectral_time[precursor_idx]
        lead_time = event.timestamp - precursor_time
        
        # Confidence: how distinct is the precursor?
        snr = broadband_energy[precursor_idx] / baseline_energy
        confidence = min(snr / self.snr_threshold, 1.0)
        
        return PrecursorCandidate(
            event_timestamp=event.timestamp,
            precursor_timestamp=precursor_time,
            lead_time=lead_time,
            confidence=confidence,
            spectral_features={
                'snr': float(snr),
                'energy_ratio': float(broadband_energy[precursor_idx] / baseline_energy),
                'entropy_ratio': float(spectral_entropy[precursor_idx] / baseline_entropy)
            }
        )
    
    def step4_measure_lead_time(self, 
                                precursors: List[PrecursorCandidate]) -> dict:
        """
        Step 4: Measure Δt honestly.
        
        For each event:
        - Earliest detectable precursor
        - Median Δt
        - Worst-case Δt
        
        Verdict:
        - Δt < control loop response → FAIL
        - Δt inconsistent → INCONCLUSIVE
        - Δt ≥ meaningful window → PASS
        """
        print("\n[STEP 4: LEAD TIME MEASUREMENT]")
        
        if not precursors:
            return {
                'status': 'FAIL',
                'reason': 'No precursors detected'
            }
        
        lead_times = np.array([p.lead_time for p in precursors])
        confidences = np.array([p.confidence for p in precursors])
        
        # Filter by SNR threshold
        valid_precursors = [p for p in precursors if p.confidence >= (1.0 / self.snr_threshold)]
        valid_lead_times = np.array([p.lead_time for p in valid_precursors])
        
        if len(valid_precursors) == 0:
            return {
                'status': 'FAIL',
                'reason': f'No precursors meet SNR threshold ({self.snr_threshold})'
            }
        
        median_dt = np.median(valid_lead_times)
        worst_dt = np.min(valid_lead_times)
        best_dt = np.max(valid_lead_times)
        std_dt = np.std(valid_lead_times)
        
        print(f"Valid precursors: {len(valid_precursors)}/{len(precursors)}")
        print(f"Lead time - Median: {median_dt:.2f}s, Worst: {worst_dt:.2f}s, Best: {best_dt:.2f}s")
        print(f"Lead time - Std Dev: {std_dt:.2f}s")
        
        # Check against minimum
        if worst_dt < self.min_lead_time:
            return {
                'status': 'FAIL',
                'reason': f'Worst-case lead time ({worst_dt:.2f}s) < minimum ({self.min_lead_time}s)',
                'median_dt': median_dt,
                'worst_dt': worst_dt
            }
        
        # Check consistency (std dev)
        if std_dt > median_dt * 0.5:  # >50% variation
            return {
                'status': 'INCONCLUSIVE',
                'reason': f'Lead time inconsistent (σ={std_dt:.2f}s, median={median_dt:.2f}s)',
                'median_dt': median_dt,
                'worst_dt': worst_dt,
                'std_dt': std_dt
            }
        
        return {
            'status': 'PASS',
            'reason': f'Lead time adequate and consistent',
            'median_dt': median_dt,
            'worst_dt': worst_dt,
            'best_dt': best_dt,
            'std_dt': std_dt
        }
    
    def run_validation(self,
                      acoustic: AcousticData,
                      throttle_events: List[ThrottleEvent]) -> dict:
        """
        Full validation protocol.
        
        Returns: PASS / INCONCLUSIVE / FAIL
        """
        print("="*80)
        print("HFT-SA NO-HARDWARE VALIDATION EXPERIMENT")
        print("="*80)
        
        # Step 1: Alignment
        alignment = self.step1_align_timelines(acoustic, throttle_events)
        valid_events = alignment['events']
        
        if len(valid_events) < 3:
            return {
                'status': 'FAIL',
                'reason': f'Insufficient events ({len(valid_events)} < 3 minimum)',
                'details': alignment
            }
        
        # Step 2: Spectral decomposition
        f, t, spectral_features = self.step2_spectral_decomposition(acoustic)
        
        # Step 3: Backward correlation
        print("\n[STEP 3: BACKWARD CORRELATION]")
        precursors = []
        for event in valid_events:
            precursor = self.step3_backward_correlation(event, t, spectral_features)
            if precursor:
                precursors.append(precursor)
                print(f"  Event at {event.timestamp:.1f}s: Precursor found (Δt={precursor.lead_time:.2f}s, conf={precursor.confidence:.2f})")
            else:
                self.missing_events.append(event.timestamp)
                print(f"  Event at {event.timestamp:.1f}s: NO PRECURSOR")
        
        # Check consistency (GATE 1)
        consistency_rate = len(precursors) / len(valid_events)
        print(f"\nConsistency: {len(precursors)}/{len(valid_events)} ({consistency_rate*100:.1f}%)")
        
        if consistency_rate < self.consistency_threshold:
            return {
                'status': 'INCONCLUSIVE',
                'reason': f'Precursor inconsistent ({consistency_rate*100:.1f}% < {self.consistency_threshold*100:.1f}%)',
                'consistency_rate': consistency_rate,
                'precursors_found': len(precursors),
                'total_events': len(valid_events)
            }
        
        # Step 4: Lead time measurement (GATE 2)
        lead_time_result = self.step4_measure_lead_time(precursors)
        
        # Final verdict
        print("\n" + "="*80)
        print(f"FINAL VERDICT: {lead_time_result['status']}")
        print("="*80)
        print(f"Reason: {lead_time_result['reason']}")
        
        return {
            'status': lead_time_result['status'],
            'reason': lead_time_result['reason'],
            'consistency_rate': consistency_rate,
            'precursors': len(precursors),
            'total_events': len(valid_events),
            'lead_time': lead_time_result.get('median_dt'),
            'lead_time_worst': lead_time_result.get('worst_dt'),
            'lead_time_std': lead_time_result.get('std_dt'),
            'timestamp': datetime.now().isoformat()
        }


# =============================================================================
# SYNTHETIC TEST DATA (for demonstration)
# =============================================================================

def generate_synthetic_test():
    """Generate synthetic data for protocol demonstration"""
    
    # Synthetic acoustic signal with precursors
    duration = 300  # 5 minutes
    fs = 10000  # 10 kHz sampling
    t = np.linspace(0, duration, duration * fs)
    
    # Baseline noise
    noise = np.random.randn(len(t)) * 0.1
    
    # Pump noise (low frequency)
    pump_noise = 0.2 * np.sin(2 * np.pi * 50 * t)  # 50 Hz
    
    # Add precursor signals before throttle events
    throttle_times = [100, 180, 250]  # seconds
    signal_data = noise + pump_noise
    
    for throttle_t in throttle_times:
        # Add turbulence signature 10s before throttle
        precursor_start = max(0, int((throttle_t - 10) * fs))
        precursor_end = int(throttle_t * fs)
        
        # Broadband turbulence (500-2000 Hz)
        turbulence = 0.5 * np.random.randn(precursor_end - precursor_start)
        for freq in [500, 800, 1200, 1500]:
            turbulence += 0.3 * np.sin(2 * np.pi * freq * np.linspace(0, 10, precursor_end - precursor_start))
        
        signal_data[precursor_start:precursor_end] += turbulence
    
    acoustic = AcousticData(
        timestamps=t,
        signal=signal_data,
        sampling_rate=fs,
        sensor_location="Cold plate accelerometer"
    )
    
    throttle_events = [
        ThrottleEvent(timestamp=t_event, node_id="node_01", 
                     temperature=85.0, event_type="throttle_start")
        for t_event in throttle_times
    ]
    
    return acoustic, throttle_events


# =============================================================================
# EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("Generating synthetic test data...")
    acoustic, throttle_events = generate_synthetic_test()
    
    # Run validation
    protocol = ValidationProtocol(
        min_lead_time=2.0,  # minimum 2 seconds
        consistency_threshold=0.8,  # must detect in 80% of events
        snr_threshold=3.0  # 10 dB SNR
    )
    
    result = protocol.run_validation(acoustic, throttle_events)
    
    # Export
    output_path = r'c:\Veritas_Lab\HFT-SA_VALIDATION_RESULT.json'
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n[EXPORT] Validation result saved to {output_path}")
    
    if result['status'] == 'PASS':
        print("\n[NEXT STEP] Proceed to Phase 2 PoC:")
        print("  1. Lightweight feature extractor")
        print("  2. Real-time streaming")
        print("  3. Shadow-mode deployment (NO ACTUATION)")
    elif result['status'] == 'INCONCLUSIVE':
        print("\n[NEXT STEP] Refine experiment:")
        print(f"  Issue: {result['reason']}")
        print("  Action: Collect more data or improve separability")
    else:  # FAIL
        print("\n[NEXT STEP] Archive project:")
        print(f"  Reason: {result['reason']}")
        print("  Action: Mark as REJECTED_SURVIVOR, move to next concept")
