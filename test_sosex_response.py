#!/usr/bin/env python3
"""
Simple test script to demonstrate the SOS executive broadcast response system.
This script simulates the fixed mqttClienttrack.py behavior.
"""

import json

def simulate_sosex_response(token, lat, lon, speed):
    """
    Simulate the Process_sosEx_Data function response
    """
    
    # Simulate the response format we expect
    mock_broadcast_data = [
        {
            "id": 112,
            "call": {
                "name": "Disaster Management",
                "detail": "night",
                "status": "Active"
            },
            "type": "police_ex",
            "status": "pending"
        },
        {
            "id": 114, 
            "call": {
                "name": "Emergency Response",
                "detail": "medical emergency",
                "status": "Active"
            },
            "type": "ambulance_ex",
            "status": "pending"
        }
    ]
    
    # This is the response format our fixed code now sends
    response = {
        "status": "success",
        "broadcast": mock_broadcast_data,
        "message": "Location updated successfully"
    }
    
    # The corrected topic format
    response_topic = f"sosEx/{token}/response"
    
    print("=== SOS Executive Broadcast Response Test ===")
    print(f"Input Message:")
    print(f"  Token: {token}")
    print(f"  Location: {lat}, {lon}")
    print(f"  Speed: {speed}")
    print(f"\nResponse Topic: {response_topic}")
    print(f"\nResponse Message:")
    print(json.dumps(response, indent=2))
    
    return response_topic, response

if __name__ == "__main__":
    # Test with the valid token that was working
    token = "b14375693556882d609e1e160a6cb16492c7a86f"
    lat = 26.133602
    lon = 91.804747 
    speed = 10
    
    topic, response = simulate_sosex_response(token, lat, lon, speed)
    
    print(f"\n=== MQTT Commands to Test ===")
    print(f"1. Subscribe to responses:")
    print(f"mosquitto_sub -h 135.235.166.209 -p 8883 --cafile /home/azureuser/Skytrack_Backend/Skytronsystem/keys/ca.crt -u admin -P adminpass -t \"{topic}\" -v")
    
    print(f"\n2. Publish SOS message:")
    print(f"mosquitto_pub -h 135.235.166.209 -p 8883 --cafile /home/azureuser/Skytrack_Backend/Skytronsystem/keys/ca.crt -u admin -P adminpass -t \"sosEx/{token}\" -m '{{\"token\":\"{token}\",\"em_lat\":{lat},\"em_lon\":{lon},\"speed\":{speed}}}'")
    
    print(f"\n=== Fix Summary ===")
    print(f"BEFORE: Responses published to sosEx/{token}")
    print(f"AFTER:  Responses published to sosEx/{token}/response")
    print(f"\nThis fix ensures SOS executives receive broadcast lists when they send location updates.")