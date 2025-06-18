#!/usr/bin/env python3
"""
Henry Apartments GitHub Actions Monitor
======================================
Runs every 30 minutes automatically on GitHub's servers!
Only sends alerts when target rooms are available.
"""

import os
import requests
import json
from datetime import datetime, timezone

# Get environment variables from GitHub Actions
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
XSRF_TOKEN = os.environ.get('XSRF_TOKEN')
BSESSION = os.environ.get('BSESSION')

# Your target rooms
TARGET_ROOMS = [
    '2 Room Apartment Ground Floor',
    'Cozy 2 Room Apartment'
]

# Booking parameters
BOOKING_CONFIG = {
    "checkIn": 1763856000000,   # Nov 23, 2025
    "checkOut": 1764201600000,  # Nov 27, 2025
    "adults": 2,
    "children": 0
}

def send_telegram_alert(message):
    """Send message to Telegram"""
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Missing Telegram credentials")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message[:4096],  # Telegram limit
            "disable_web_page_preview": False
        }
        
        response = requests.post(url, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Telegram message sent successfully!")
                return True
            else:
                print(f"❌ Telegram API error: {result}")
                return False
        else:
            print(f"❌ HTTP error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception sending Telegram: {e}")
        return False

def check_room_availability():
    """Check Henry's Apartments for target room availability"""
    try:
        print(f"🔍 Checking availability at {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
        
        # API headers and cookies
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://hotels.wixapps.net",
            "x-wix-instance": "tMyA8veD0LlWINpkMjEVGWoPRCGrS_hx98scw60rUf4.eyJpbnN0YW5jZUlkIjoiNjU1ZjBlNzEtOTVmOC00YzYwLWIxM2ItYTYxOGNmNDAxN2FmIiwi"
                             "YXBwRGVmSWQiOiIxMzVhYWQ4Ni05MTI1LTYwNzQtNzM0Ni0yOWRjNmEzYzliY2YiLCJtZXRh"
                             "U2l0ZUlkIjoiZGJkZmVmNWUtZWY3YS00YmFiLWFlOWMtYTI5ZWQ3YmQ0N2ExIiwic2lnbkRh"
                             "dGUiOiIyMDI1LTA2LTE3VDA4OjM4OjQwLjEwMVoiLCJ2ZW5kb3JQcm9kdWN0SWQiOiJob3Rl"
                             "bHMiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiI4MDBiYzdlMC1hNTgx"
                             "LTRkYzQtODdjNi1kYTNiNzUyMzI0OTEiLCJhaWQiOiJmYTVjMjAyZi0zNDNiLTQyZjAtOWI1"
                             "MC0wNDNhMWM3MzJmZjMiLCJiaVRva2VuIjoiYmU4MGUxMmYtN2E4Mi0wN2NiLTFmYTctMDQ4"
                             "NjE4ZmQ1MDBlIiwic2l0ZU93bmVySWQiOiIxOTMxYTIxNC0wNDIyLTQ2MzYtOTdkMS04MDJl"
                             "MjkzYzUyMmUiLCJicyI6IjNvMXNaeWphTGNqa2pwSnRRaTNlZVl4Q01YUGRtXzkyem4xVFdY"
                             "eE1sSzgiLCJzY2QiOiIyMDIyLTAxLTIwVDE1OjUyOjEyLjkzNFoifQ",
            "x-xsrf-token": XSRF_TOKEN,
        }
        
        cookies = {
            "XSRF-TOKEN": XSRF_TOKEN,
            "bSession": BSESSION,
        }
        
        # Make API request
        response = requests.post(
            "https://hotels.wixapps.net/api/rooms/search",
            headers=headers,
            cookies=cookies,
            json=BOOKING_CONFIG,
            timeout=20
        )
        
        print(f"📡 API Response: {response.status_code}")
        
        if response.status_code == 403:
            error_msg = "🚨 Authentication Failed!\n\nYour XSRF_TOKEN or BSESSION has expired.\nPlease update the GitHub secrets with fresh tokens."
            print("❌ 403 Forbidden - Tokens expired")
            send_telegram_alert(error_msg)
            return
        
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return
        
        # Parse response
        rooms_data = response.json()
        print(f"📊 Total rooms in response: {len(rooms_data)}")
        
        # Filter for available target rooms
        available_target_rooms = []
        
        for room_item in rooms_data:
            # Skip sold out rooms
            if room_item.get("soldOut", False):
                continue
                
            room = room_item.get("room", {})
            room_name = room.get("name", "")
            
            # Check if this is one of our target rooms
            for target_room in TARGET_ROOMS:
                if target_room.lower() in room_name.lower():
                    available_target_rooms.append(room_item)
                    print(f"🎯 TARGET ROOM FOUND: {room_name}")
                    break
        
        # Send alert if target rooms are available
        if available_target_rooms:
            send_room_alert(available_target_rooms)
        else:
            print("😴 No target rooms available - continuing silent monitoring")
    
    except Exception as e:
        print(f"💥 Error during check: {e}")
        error_msg = f"🚨 Henry's Monitor Error\n\nTime: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\nError: {str(e)[:300]}\n\nMonitoring continues..."
        send_telegram_alert(error_msg)

def send_room_alert(available_rooms):
    """Send alert for available target rooms"""
    try:
        # Calculate dates and nights
        checkin_date = datetime.fromtimestamp(BOOKING_CONFIG["checkIn"]/1000, tz=timezone.utc)
        checkout_date = datetime.fromtimestamp(BOOKING_CONFIG["checkOut"]/1000, tz=timezone.utc)
        nights = (BOOKING_CONFIG["checkOut"] - BOOKING_CONFIG["checkIn"]) // (1000 * 60 * 60 * 24)
        
        # Build alert message
        message_lines = [
            "🚨 TARGET ROOMS AVAILABLE! 🚨",
            "🏨 HENRY'S APARTMENTS INTERLAKEN",
            "═══════════════════════════════════",
            "",
            f"📅 Check-in:  {checkin_date:%d %b %Y}",
            f"📅 Check-out: {checkout_date:%d %b %Y}",
            f"🌙 Nights:    {nights}",
            f"👥 Guests:    {BOOKING_CONFIG['adults']} adults, {BOOKING_CONFIG['children']} children",
            "",
            "🎯 YOUR TARGET ROOMS ARE AVAILABLE:",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        
        # Add room details
        for i, room_item in enumerate(available_rooms, 1):
            room = room_item["room"]
            price = room["price"]
            
            message_lines.extend([
                "",
                f"✅ {i}. {room['name']}",
                f"   💰 {price['amount']} {price['currency']} per night"
            ])
            
            # Calculate total cost
            try:
                total_cost = int(price['amount']) * nights
                message_lines.append(f"   💵 Total: {total_cost} {price['currency']} ({nights} nights)")
            except:
                message_lines.append(f"   💵 Total: {price['amount']} x {nights} nights")
            
            # Add room details
            if room.get('maxPersons'):
                message_lines.append(f"   👥 Max guests: {room['maxPersons']}")
            if room.get('size'):
                message_lines.append(f"   📐 Size: {room['size']} m²")
            if room.get('roomId'):
                message_lines.append(f"   🆔 Room ID: {room['roomId']}")
        
        # Add booking links
        booking_url = f"https://www.henrysinterlaken.com/zimmer-buchen/rooms/?checkIn={BOOKING_CONFIG['checkIn']}&checkOut={BOOKING_CONFIG['checkOut']}&adults={BOOKING_CONFIG['adults']}&children={BOOKING_CONFIG['children']}&lang=en"
        
        message_lines.extend([
            "",
            "🚀 BOOK NOW - DON'T MISS OUT!",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🔗 Direct booking link:",
            booking_url,
            "",
            "📞 Alternative booking (faster):",
            "• Phone: +41 (0) 79 855 38 00",
            "• Email: henrysinterlaken@gmail.com",
            "",
            "⚡ URGENT: These rooms may sell out quickly!",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"🕐 Found: {datetime.now(timezone.utc):%d %b %Y at %H:%M} UTC",
            "🤖 Monitored by GitHub Actions"
        ])
        
        message = "\n".join(message_lines)
        
        if send_telegram_alert(message):
            print(f"🎉 ALERT SENT! Found {len(available_rooms)} target room(s)")
        else:
            print(f"❌ Failed to send alert for {len(available_rooms)} rooms")
    
    except Exception as e:
        print(f"❌ Error building room alert: {e}")

def main():
    """Main execution function"""
    print("🤖 Henry's Apartments GitHub Actions Monitor")
    print("=" * 50)
    print(f"🎯 Target Rooms: {', '.join(TARGET_ROOMS)}")
    print(f"📅 Dates: {datetime.fromtimestamp(BOOKING_CONFIG['checkIn']/1000, tz=timezone.utc):%d %b} - {datetime.fromtimestamp(BOOKING_CONFIG['checkOut']/1000, tz=timezone.utc):%d %b %Y}")
    print(f"👥 Guests: {BOOKING_CONFIG['adults']} adults, {BOOKING_CONFIG['children']} children")
    print("")
    
    # Validate environment variables
    missing_vars = []
    if not BOT_TOKEN: missing_vars.append("BOT_TOKEN")
    if not CHAT_ID: missing_vars.append("CHAT_ID") 
    if not XSRF_TOKEN: missing_vars.append("XSRF_TOKEN")
    if not BSESSION: missing_vars.append("BSESSION")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please add these as GitHub repository secrets!")
        return
    
    print("✅ All environment variables present")
    
    # Run the check
    check_room_availability()
    print("✅ Check completed")

if __name__ == "__main__":
    main()
