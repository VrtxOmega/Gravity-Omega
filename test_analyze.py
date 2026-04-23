#!/usr/bin/env python3
"""
Test script for the VERITAS Flask API analyzer
"""

import requests
import json

def test_analyze_endpoint():
    """Test the /analyze endpoint with sample code"""
    
    # Sample Python code to test
    test_code = '''
def hello_world():
    print("Hello, World!")
    return "Success"

# This should pass VERITAS gates
class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
'''
    
    # Test malicious code example
    malicious_code = '''
import os
import subprocess

def dangerous_function():
    # This should trigger violations
    os.system("rm -rf /")
    subprocess.call(["shutdown", "-h", "now"])
    return "Dangerous code executed"
'''
    
    url = "http://localhost:5000/analyze"
    
    print("Testing VERITAS Flask API...")
    print("=" * 50)
    
    # Test 1: Valid code
    print("\n1. Testing valid Python code:")
    response = requests.post(url, json={'code': test_code})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test 2: Malicious code
    print("\n2. Testing potentially malicious code:")
    response = requests.post(url, json={'code': malicious_code})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test 3: Empty request
    print("\n3. Testing empty code:")
    response = requests.post(url, json={'code': ''})
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Test 4: Invalid JSON
    print("\n4. Testing invalid JSON:")
    try:
        response = requests.post(url, data="not json")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_analyze_endpoint()