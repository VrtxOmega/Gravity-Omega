"""
EDGE-AUDIT MVP - ENHANCED PARSER V4
Final push to 92% detection

V4 improvements:
- Simplified ND-without-value detection
- Test each pattern individually with debug output
- Hand-tuned for LINAK/Samsung ND formats
"""

import re
from typing import Dict, List

# Simplified patterns - each substance gets tried in order
PATTERNS = {
    'lead': [
        r'(?:lead|pb|\u94c5)\\s*(?:\\(pb\\))?\\s*(?:content)?\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'\\|\\s*(?:lead)\\s*(?:\\([^\\)]+\\))?\\s*\\|[^\\|]*\\|\\s*<?\\s*(\\d+(?:\\.\\d+)?)\\s*(?:ppm|%)',  # Table
    ],
    'mercury': [
        r'(?:mercury|hg|\u6c5e)\\s*(?:\\(hg\\))?\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:mercury|hg|\u6c5e)\\s*[:=]?\\s*(?:nd|not\\s*detected|\u68c0\u6d4b\u4e0d\u5230)\\s*\\(<?(\\d+(?:\\.\\d+)?)\\s*ppm\\)',  # ND with value
        r'(?:\u6c5e|mercury\\s*\\(hg\\))\\s*[:=]?\\s*(?:\u68c0\u6d4b\u4e0d\u5230|not\\s*detected)',  # ND without value (returns None)
    ],
    'cadmium': [
        r'(?:cadmium|cd|\u9549)\\s*(?:\\(cd\\))?\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:cadmium|cd|\u9549)\\s*[:=]?\\s*(?:nd|not\\s*detected)\\s*\\(<?(\\d+(?:\\.\\d+)?)\\s*ppm\\)',
    ],
    'hexavalent_chromium': [
        r'(?:hexavalent\\s+chromium)\\s*(?:\\(\\s*cr\\s+vi\\s*\\))?\\s*[:=]?\\s*<?\\s*(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:cr\\s*vi|cr\\(vi\\)|\u516d\u4ef7\u94ec|cr6\\+)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:\u516d\u4ef7\u94ec|cr\\(vi\\))\\s*[:=]?\\s*(?:\u68c0\u6d4b\u4e0d\u5230|nd)',  # Chinese ND
    ],
    'pbb': [
        r'(?:pbb)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:pbb/pbde)\\s*[:=]?\\s*(?:nd|not\\s*detected)\\s*\\(<(\\d+(?:\\.\\d+)?)\\s*ppm\\)',
        r'(?:pbb)\\s*[:=]?\\s*(?:nd|not\\s*detected)\\s*\\(<(\\d+(?:\\.\\d+)?)\\s*ppm\\)',
        r'pbb\\s*[:=]?\\s*not\\s*detected(?!\\s*\\()',  # ND without parentheses (returns None)
    ],
    'pbde': [
        r'(?:pbde)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:pbb/pbde)\\s*[:=]?\\s*(?:nd|not\\s*detected)\\s*\\(<(\\d+(?:\\.\\d+)?)\\s*ppm\\)',
        r'(?:pbde)\\s*[:=]?\\s*(?:nd|not\\s*detected)\\s*\\(<(\\d+(?:\\.\\d+)?)\\s*ppm\\)',
        r'pbde\\s*[:=]?\\s*not\\s*detected(?!\\s*\\()',  # ND without parentheses
    ],
    'pfoa': [
        r'(?:pfoa)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppb',
        r'(?:pfoa)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppm',
    ],
    'pfos': [
        r'(?:pfos)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppb',
        r'(?:pfos)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppm',
    ],
    'pfhxs': [
        r'(?:pfhxs)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppt',
        r'(?:pfhxs)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppb',
        r'(?:pfhxs)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppm',
    ],
    'pfas': [
        r'(?:pfas)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppt',
        r'(?:pfas)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppb',
        r'(?:pfas)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*ppm',
    ],
    'dehp': [
        r'(?:dehp|\u90bb\u82ef\u4e8c\u7532\u9178\u4e8c\\(2-\u4e59\u57fa\u5df1\u57fa\\)\u916f)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'\\|\\s*dehp\\s*\\|[^\\|]*\\|\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|%)',
        r'(?:pht halates|phthalate)\\s*\\((?:[^\\)]*)dehp(?:[^\\)]*)\\)\\s*[:=]?\\s*nd\\s*\\(<(\\d+)\\s*ppm\\)',
    ],
    'dbp': [
        r'(?:dbp)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:phthalates|phthalate)\\s*\\((?:[^\\)]*)dbp(?:[^\\)]*)\\)\\s*[:=]?\\s*nd\\s*\\(<(\\d+)\\s*ppm\\)',
        r'dbp\\s*[:=]?\\s*not\\s*detected(?!\\s*\\()',  # ND without value
    ],
    'bbp': [
        r'(?:bbp|\u90bb\u82ef\u4e8c\u7532\u9178\u4e01\u82c4\u916f)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:phthalates|phthalate)\\s*\\((?:[^\\)]*)bbp(?:[^\\)]*)\\)\\s*[:=]?\\s*nd\\s*\\(<(\\d+)\\s*ppm\\)',
        r'bbp\\s*[:=]?\\s*not\\s*detected(?!\\s*\\()',
    ],
    'dibp': [
        r'(?:dibp)\\s*[:=]?\\s*<?(\\d+(?:\\.\\d+)?)\\s*(?:ppm|mg/kg)',
        r'(?:phthalates|phthalate)\\s*\\((?:[^\\)]*)dibp(?:[^\\)]*)\\)\\s*[:=]?\\s*nd\\s*\\(<(\\d+)\\s*ppm\\)',
        r'dibp\\s*[:=]?\\s*not\\s*detected(?!\\s*\\()',
    ],
}


def parse_declaration_v4(text: str) -> Dict[str, float]:
    """V4 parser with simplified ND handling."""
    text_lower = text.lower()
    substances = {}
    
    for substance, patterns in PATTERNS.items():
        for pattern in patterns:
            # Search for pattern
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                # Check if pattern has capture group
                groups = match.groups()
                if groups and groups[0]:
                    # Has numeric value
                    try:
                        value = float(groups[0])
                        
                        # ppb/ppt conversion if needed
                        if 'ppb' in pattern:
                            value = value / 1000.0
                        elif 'ppt' in pattern:
                            value = value / 1_000_000.0
                        
                        substances[substance] = value
                        break  # Found value, move to next substance
                    except ValueError:
                        continue  # Bad match, try next pattern
                else:
                    # No capture group or empty capture = "Not Detected" without value
                    substances[substance] = 0.0  # Assume compliant
                    break
    
    return substances


def test_v4_parser():
    """Test V4 with realistic samples."""
    
    test_samples = [
        {
            'name': 'LINAK',
            'expected': 10,
            'text': """
DECLARATION OF CONFORMITY TO EU RoHS

Lead (Pb):                850 ppm    (Limit: 1000 ppm) - COMPLIANT
Mercury (Hg):             <50 ppm    (Limit: 1000 ppm) - COMPLIANT  
Cadmium (Cd):             75 ppm     (Limit: 100 ppm) - COMPLIANT
Hexavalent Chromium (Cr VI): 120 ppm (Limit: 1000 ppm) - COMPLIANT
PBB:                      Not Detected
PBDE:                     Not Detected
DEHP:                     650 ppm    (Limit: 1000 ppm) - COMPLIANT
BBP:                      <100 ppm
DBP:                      <100 ppm
DIBP:                     <100 ppm
            """
        },
        {
            'name': 'Advanced Energy',
            'expected': 11,
            'text': """
RoHS 3 Compliance Declaration

Lead (Pb) content:                  1200 ppm - NON-COMPLIANT
Mercury (Hg):                       ND (<100 ppm)
Cadmium (Cd):                       ND (<100 ppm)  
Cr(VI):                             ND (<100 ppm)
PBB/PBDE:                           ND (<1000 ppm)
Phthalates (DEHP/BBP/DBP/DIBP):    ND (<1000 ppm)

Additional Testing (PFAS):
PFOA:                               <10 ppb (25 ppm limit)
PFOS:                               35 ppm - EXCEEDS EU limit
            """
        },
        {
            'name': 'Shenzhen',
            'expected': 6,
            'text': """
物质声明 Material Declaration

铅 Lead (Pb):              950 mg/kg  
汞 Mercury (Hg):           检测不到 Not Detected
镉 Cadmium (Cd):           80 mg/kg
六价铬 Cr(VI):             检测不到 ND  

REACH SVHC:
邻苯二甲酸二(2-乙基己基)酯 DEHP: 1200 ppm
邻苯二甲酸丁苄酯 BBP: <500 ppm
            """
        },
        {
            'name': 'Anton Paar',
            'expected': 2,
            'text': """
REACH - Supplier's Declaration

| Substance Name | CAS Number | Concentration | Location |
|----------------|------------|---------------|----------|
| Lead (Pb)      | 7439-92-1  | 1500 ppm | Electronic components |
| DEHP | 117-81-7 | 2500 ppm | Cable insulation |
            """
        },
        {
            'name': 'Samsung',
            'expected': 10,
            'text': """
DECLARATION OF RoHS COMPLIANCE

Lead (Pb):                  <500 ppm (Compliant)
Mercury (Hg):               <50 ppm (Compliant)
Cadmium (Cd):               <20 ppm (Compliant)  
Hexavalent Chromium:        <50 ppm (Compliant)
PBB:                        Not Detected (<500 ppm)
PBDE:                       Not Detected (<500 ppm)
DEHP:                       <300 ppm (Compliant)
BBP:                        Not Detected
DBP:                        Not Detected  
DIBP:                       Not Detected
            """
        }
    ]
    
    print("="*80)
    print("EDGE-AUDIT PARSER V4 - FINAL TEST")
    print("="*80)
    
    total_detected = 0
    total_expected = 0
    
    for sample in test_samples:
        substances = parse_declaration_v4(sample['text'])
        detected = len(substances)
        expected = sample['expected']
        
        total_detected += detected
        total_expected += expected
        
        print(f"\\n{sample['name']}: {detected}/{expected} ({detected/expected*100:.0%})")
        for sub, val in sorted(substances.items()):
            print(f"  - {sub}: {val} ppm")
    
    detection_rate = total_detected / total_expected
    
    print(f"\\n" + "="*80)
    print(f"OVERALL: {total_detected}/{total_expected} = {detection_rate:.1%}")
    
    if detection_rate >= 0.92:
        print("[PASS] ✓ 92% target achieved!")
    else:
        print(f"[MISS] Need {int((0.92 - detection_rate) * total_expected)} more substances")
        print(f"Gap: {0.92 - detection_rate:.1%}")
    print("="*80)


if __name__ == "__main__":
    import sys
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Edge-Audit ESG Parser V4")
    parser.add_argument("--context", type=str, help="Path to context file containing ESG text")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    args, unknown = parser.parse_known_args()

    if args.test or len(sys.argv) == 1:
        test_v4_parser()
    elif args.context:
        try:
            with open(args.context, "r", encoding="utf-8") as f:
                text = f.read()
            substances = parse_declaration_v4(text)
            print("EDGE_AUDIT_PARSED:")
            print(json.dumps(substances, indent=2))
        except Exception as e:
            print(f"Error parsing context: {e}", file=sys.stderr)
            sys.exit(1)
