"""Test script to validate FCC query endpoints and response schemas."""

import requests
from pathlib import Path

def test_fcc_fm_query():
    """Test FCC FM query endpoint with exact URL provided."""
    
    # Exact URL from user specification - DO NOT CHANGE PARAMETERS
    fm_url = "https://transition.fcc.gov/fcc-bin/fmq?call=&filenumber=&state=&city=&freq=88.1&fre2=107.9&serv=FM&status=3&facid=&asrn=&class=&list=4&NextTab=Results+to+Next+Page%2FTab&dist=&dlat2=&mlat2=&slat2=&NS=N&dlon2=&mlon2=&slon2=&EW=W&size=9"
    
    print("Testing FCC FM Query endpoint...")
    print(f"URL: {fm_url}")
    
    try:
        response = requests.get(fm_url, timeout=60)  # Longer timeout for full dataset
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"Content Length: {len(response.text)} characters")
        
        if response.status_code == 200:
            # Save sample response
            sample_file = Path("sample_fm_full_response.txt")
            sample_file.write_text(response.text[:10000])  # First 10KB
            print(f"Sample response saved to {sample_file}")
            
            # Analyze the data
            lines = response.text.strip().split('\n')
            print(f"Total lines: {len(lines)}")
            
            if lines and lines[0].strip():
                # Show first few lines
                print("\nFirst 10 lines of response:")
                for i, line in enumerate(lines[:10], 1):
                    print(f"{i:2d}: {line}")
                
                # Analyze pipe-delimited format
                first_line = lines[0]
                fields = first_line.split('|')
                print(f"\nField count: {len(fields)}")
                print("Sample fields:")
                for i, field in enumerate(fields[:8]):  # Show first 8 fields
                    print(f"  {i}: '{field.strip()}'")
            else:
                print("No data returned or empty response")
                
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.RequestException as e:
        print(f"Request failed: {e}")

def test_fcc_am_query():
    """Test FCC AM query endpoint with exact URL provided."""
    
    # Exact URL from user specification - DO NOT CHANGE PARAMETERS
    am_url = "https://transition.fcc.gov/fcc-bin/amq?call=&filenumber=&state=&city=&freq=530&fre2=1700&type=3&facid=&class=&hours=&list=4&NextTab=Results+to+Next+Page%2FTab&dist=&dlat2=&mlat2=&slat2=&NS=N&dlon2=&mlon2=&slon2=&EW=W&size=9"
    
    print("\n" + "="*60)
    print("Testing FCC AM Query endpoint...")
    print(f"URL: {am_url}")
    
    try:
        response = requests.get(am_url, timeout=60)  # Longer timeout for full dataset
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"Content Length: {len(response.text)} characters")
        
        if response.status_code == 200:
            # Save sample response
            sample_file = Path("sample_am_full_response.txt")
            sample_file.write_text(response.text[:10000])  # First 10KB
            print(f"Sample response saved to {sample_file}")
            
            # Analyze the data
            lines = response.text.strip().split('\n')
            print(f"Total lines: {len(lines)}")
            
            if lines and lines[0].strip():
                print("First 10 lines of AM response:")
                for i, line in enumerate(lines[:10], 1):
                    print(f"{i:2d}: {line}")
                
                # Analyze pipe-delimited format
                first_line = lines[0]
                fields = first_line.split('|')
                print(f"\nField count: {len(fields)}")
                print("Sample fields:")
                for i, field in enumerate(fields[:8]):  # Show first 8 fields
                    print(f"  {i}: '{field.strip()}'")
            else:
                print("No data returned or empty response")
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.RequestException as e:
        print(f"Request failed: {e}")

def test_query_without_params():
    """Test queries without parameters to see the form structure."""
    
    print("\n" + "="*60)
    print("Testing query endpoints without parameters...")
    
    for name, url in [("FM", "https://transition.fcc.gov/fcc-bin/fmq"), 
                      ("AM", "https://transition.fcc.gov/fcc-bin/amq")]:
        print(f"\n{name} Query Form:")
        try:
            response = requests.get(url, timeout=15)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                # Look for form fields in the HTML
                content = response.text.lower()
                if 'form' in content:
                    print("Contains HTML form ✓")
                if 'input' in content:
                    print("Contains input fields ✓")
                if 'select' in content:
                    print("Contains select fields ✓")
        except Exception as e:
            print(f"Failed: {e}")

def test_geo_fcc_apis():
    """Test current working geo.fcc.gov APIs."""
    
    print("\n" + "="*60)
    print("Testing FCC geo.fcc.gov APIs...")
    
    # Test 1: Area/Census API
    area_url = "https://geo.fcc.gov/api/census/area"
    area_params = {
        'format': 'json',
        'lat': 37.7749,  # San Francisco
        'lon': -122.4194
    }
    
    print(f"\n1. Testing Area API: {area_url}")
    print(f"   Parameters: {area_params}")
    
    try:
        response = requests.get(area_url, params=area_params, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response keys: {list(data.keys())}")
            print(f"   Sample: {str(data)[:200]}...")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    # Test 2: Contours API for a known FM station
    contours_url = "https://geo.fcc.gov/api/contours"
    contours_params = {
        'format': 'json',
        'callsign': 'KQED'  # San Francisco public radio
    }
    
    print(f"\n2. Testing Contours API: {contours_url}")
    print(f"   Parameters: {contours_params}")
    
    try:
        response = requests.get(contours_url, params=contours_params, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response keys: {list(data.keys())}")
            print(f"   Sample: {str(data)[:200]}...")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Failed: {e}")

def test_fcc_search_alternatives():
    """Test alternative FCC data access methods."""
    
    print("\n" + "="*60)
    print("Testing alternative FCC data sources...")
    
    # Test fccdata.org (third-party but reliable)
    print("\n1. Testing fccdata.org...")
    try:
        response = requests.get("https://fccdata.org", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   fccdata.org accessible ✓")
    except Exception as e:
        print(f"   Failed: {e}")

def test_digital_frequency_search():
    """Test DigitalFrequencySearch CSV download."""
    
    print("\n" + "="*60)
    print("Testing DigitalFrequencySearch CSV download...")
    
    # Test the main page first
    main_url = "https://digitalfrequencysearch.com/Search/FMPFrequencyFile.php"
    
    print(f"\n1. Testing main page: {main_url}")
    try:
        response = requests.get(main_url, timeout=15)
        print(f"   Status: {response.status_code}")
        print(f"   Content length: {len(response.text)} chars")
        
        if response.status_code == 200:
            # Look for download links in the content
            content = response.text.lower()
            if 'csv' in content:
                print("   Page mentions CSV downloads ✓")
            if 'download' in content:
                print("   Page has download links ✓")
            
            # Show a snippet to see format
            lines = response.text.split('\n')[:10]
            print("\n   Page preview:")
            for line in lines:
                if line.strip():
                    print(f"     {line[:80]}...")
                    
    except Exception as e:
        print(f"   Failed: {e}")
        
    # Test FCC official FM/AM search pages
    print(f"\n2. Testing FCC FM Query page...")
    try:
        fm_url = "https://www.fcc.gov/media/radio/fm-query"
        response = requests.get(fm_url, timeout=15)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   FCC FM Query accessible ✓")
    except Exception as e:
        print(f"   Failed: {e}")

if __name__ == "__main__":
    test_fcc_fm_query()
    test_fcc_am_query()