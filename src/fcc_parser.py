"""Parser for FCC pipe-delimited radio station data."""

import requests
import re
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Tuple

class RadioStation(BaseModel):
    """Radio station data structure with validation."""
    call_sign: str = Field(..., description="Station call sign")
    frequency: float = Field(..., gt=0, description="Frequency in MHz")
    service_type: str = Field(..., pattern="^(FM|AM)$", description="Service type")
    city: str = Field(..., description="City of license")
    state: str = Field(..., max_length=2, description="State abbreviation")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude in degrees")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude in degrees")
    power_watts: Optional[float] = Field(None, ge=0, description="Power in watts")
    licensee: Optional[str] = Field(None, description="License holder")
    facility_id: Optional[str] = Field(None, description="FCC facility ID")
    status: Optional[str] = Field(None, description="License status")
    
    @field_validator('frequency')
    @classmethod
    def validate_frequency(cls, v, info):
        """Validate frequency ranges for FM/AM."""
        # Note: service_type validation happens after frequency in Pydantic v2
        # We'll do a basic range check here
        if not (0.53 <= v <= 107.9):
            raise ValueError('Frequency must be between 0.53 and 107.9 MHz')
        return v
    
    @field_validator('call_sign')
    @classmethod
    def validate_call_sign(cls, v):
        """Validate call sign format - preserve FCC data as presented."""
        if not v:
            raise ValueError('Call sign cannot be empty')
        # Allow "-" as it appears to be FCC placeholder for vacant allocations
        return v.strip()
    
    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True
        validate_assignment = True
    
class FCCDataFetcher:
    """Fetches and parses FCC radio station data."""
    
    # Exact URLs provided by user - DO NOT CHANGE
    FM_URL = "https://transition.fcc.gov/fcc-bin/fmq?call=&filenumber=&state=&city=&freq=88.1&fre2=107.9&serv=FM&status=3&facid=&asrn=&class=&list=4&NextTab=Results+to+Next+Page%2FTab&dist=&dlat2=&mlat2=&slat2=&NS=N&dlon2=&mlon2=&slon2=&EW=W&size=9"
    AM_URL = "https://transition.fcc.gov/fcc-bin/amq?call=&filenumber=&state=&city=&freq=530&fre2=1700&type=3&facid=&class=&hours=&list=4&NextTab=Results+to+Next+Page%2FTab&dist=&dlat2=&mlat2=&slat2=&NS=N&dlon2=&mlon2=&slon2=&EW=W&size=9"
    
    # Field mappings based on observed data structure
    # These can be updated as we discover incorrect assumptions
    FM_FIELDS = {
        'call_sign': 1,
        'frequency': 2,
        'service_type': 3,
        'status': 9,
        'city': 10,
        'state': 11,
        'country': 12,
        'facility_id': 13,
        'power': 14,
        'lat_direction': 19,  # N/S
        'lat_degrees': 20,
        'lat_minutes': 21,
        'lat_seconds': 22,
        'lon_direction': 23,  # E/W
        'lon_degrees': 24,
        'lon_minutes': 25,
        'lon_seconds': 26,
        # licensee is typically in a longer field around position 27-35
    }
    
    AM_FIELDS = {
        'call_sign': 1,
        'frequency': 2,
        'service_type': 3,
        'status': 9,
        'city': 10,
        'state': 11,
        'country': 12,
        'facility_id': 13,
        'power': 14,
        'lat_direction': 19,  # N/S
        'lat_degrees': 20,
        'lat_minutes': 21,
        'lat_seconds': 22,
        'lon_direction': 23,  # E/W
        'lon_degrees': 24,
        'lon_minutes': 25,
        'lon_seconds': 26,
        # licensee is typically in a longer field around position 27-35
    }
    
    def fetch_fm_stations(self) -> List[RadioStation]:
        """Fetch and parse FM station data."""
        print("Fetching FM station data...")
        response = requests.get(self.FM_URL, timeout=120)
        response.raise_for_status()
        
        stations = []
        lines = response.text.strip().split('\n')
        print(f"Processing {len(lines)} FM stations...")
        
        for line_num, line in enumerate(lines, 1):
            try:
                station = self._parse_fm_line(line)
                if station:
                    stations.append(station)
            except Exception as e:
                print(f"Error parsing FM line {line_num}: {e}")
                continue
                
        print(f"Successfully parsed {len(stations)} FM stations")
        return stations
    
    def fetch_am_stations(self) -> List[RadioStation]:
        """Fetch and parse AM station data."""
        print("Fetching AM station data...")
        response = requests.get(self.AM_URL, timeout=120)
        response.raise_for_status()
        
        stations = []
        lines = response.text.strip().split('\n')
        print(f"Processing {len(lines)} AM stations...")
        
        for line_num, line in enumerate(lines, 1):
            try:
                station = self._parse_am_line(line)
                if station:
                    stations.append(station)
            except Exception as e:
                print(f"Error parsing AM line {line_num}: {e}")
                continue
                
        print(f"Successfully parsed {len(stations)} AM stations")
        return stations
    
    def _parse_fm_line(self, line: str) -> Optional[RadioStation]:
        """Parse a single FM station line using field mappings."""
        fields = line.split('|')
        if len(fields) < max(self.FM_FIELDS.values()):  # Need minimum fields
            return None
            
        try:
            # Extract key fields using field mappings
            call_sign = self._get_field(fields, self.FM_FIELDS, 'call_sign')
            if not call_sign:
                return None
                
            # Parse frequency (e.g., "88.1  MHz")
            freq_str = self._get_field(fields, self.FM_FIELDS, 'frequency')
            frequency = self._parse_frequency(freq_str)
            if not frequency:
                return None
                
            city = self._get_field(fields, self.FM_FIELDS, 'city')
            state = self._get_field(fields, self.FM_FIELDS, 'state')
            
            # Parse coordinates using field mappings
            lat, lon = self._parse_coordinates(fields, self.FM_FIELDS)
            
            # Parse power (kW to watts)
            power_str = self._get_field(fields, self.FM_FIELDS, 'power')
            power_watts = self._parse_power(power_str)
            
            # Find licensee field (longer field in later positions)
            licensee = self._find_licensee_field(fields)
            
            facility_id = self._get_field(fields, self.FM_FIELDS, 'facility_id')
            status = self._get_field(fields, self.FM_FIELDS, 'status')
            
        except Exception as e:
            print(f"Error parsing FM fields: {e}")
            return None
        
        return RadioStation(
            call_sign=call_sign,
            frequency=frequency,
            service_type="FM",
            city=city,
            state=state,
            latitude=lat,
            longitude=lon,
            power_watts=power_watts,
            licensee=licensee,
            facility_id=facility_id,
            status=status
        )
    
    def _parse_am_line(self, line: str) -> Optional[RadioStation]:
        """Parse a single AM station line using field mappings."""
        fields = line.split('|')
        if len(fields) < max(self.AM_FIELDS.values()):  # Need minimum fields
            return None
            
        try:
            # Extract key fields using field mappings
            call_sign = self._get_field(fields, self.AM_FIELDS, 'call_sign')
            if not call_sign:
                return None
                
            # Parse frequency (e.g., "540   kHz")
            freq_str = self._get_field(fields, self.AM_FIELDS, 'frequency')
            frequency = self._parse_frequency(freq_str)
            if not frequency:
                return None
                
            city = self._get_field(fields, self.AM_FIELDS, 'city')
            state = self._get_field(fields, self.AM_FIELDS, 'state')
            
            # Parse coordinates using field mappings
            lat, lon = self._parse_coordinates(fields, self.AM_FIELDS)
            
            # Parse power (kW to watts)
            power_str = self._get_field(fields, self.AM_FIELDS, 'power')
            power_watts = self._parse_power(power_str)
            
            # Find licensee field (longer field in later positions)
            licensee = self._find_licensee_field(fields)
            
            facility_id = self._get_field(fields, self.AM_FIELDS, 'facility_id')
            status = self._get_field(fields, self.AM_FIELDS, 'status')
            
        except Exception as e:
            print(f"Error parsing AM fields: {e}")
            return None
        
        return RadioStation(
            call_sign=call_sign,
            frequency=frequency,
            service_type="AM",
            city=city,
            state=state,
            latitude=lat,
            longitude=lon,
            power_watts=power_watts,
            licensee=licensee,
            facility_id=facility_id,
            status=status
        )
    
    def _parse_frequency(self, freq_str: str) -> Optional[float]:
        """Parse frequency string to float (in MHz for FM, kHz for AM)."""
        if not freq_str:
            return None
            
        # Extract number from string like "88.1  MHz" or "540   kHz"
        match = re.search(r'(\d+(?:\.\d+)?)', freq_str)
        if not match:
            return None
            
        freq = float(match.group(1))
        
        # Convert kHz to MHz for AM stations
        if 'kHz' in freq_str or freq < 30:  # AM frequencies are in kHz or < 30 MHz
            freq = freq / 1000.0  # Convert kHz to MHz
            
        return freq
    
    def _parse_power(self, power_str: str) -> Optional[float]:
        """Parse power string to watts."""
        if not power_str or power_str == '-':
            return None
            
        # Extract number from string like "2.5    kW"
        match = re.search(r'(\d+(?:\.\d+)?)', power_str)
        if not match:
            return None
            
        power_kw = float(match.group(1))
        return power_kw * 1000  # Convert kW to watts
    
    def _get_field(self, fields: List[str], field_map: dict, field_name: str) -> str:
        """Safely get a field from the fields list using the field mapping."""
        field_index = field_map.get(field_name)
        if field_index is None or field_index >= len(fields):
            return ""
        return fields[field_index].strip()
    
    def _find_licensee_field(self, fields: List[str]) -> str:
        """Find the licensee field (typically a longer field in later positions)."""
        for i in range(25, min(len(fields), 35)):
            field_content = fields[i].strip()
            if field_content and len(field_content) > 10:
                return field_content
        return ""
    
    def _parse_coordinates(self, fields: List[str], field_map: dict) -> Tuple[Optional[float], Optional[float]]:
        """Parse coordinates using field mappings."""
        try:
            # Get coordinate components using field mappings
            lat_deg_str = self._get_field(fields, field_map, 'lat_degrees')
            lat_min_str = self._get_field(fields, field_map, 'lat_minutes')
            lat_sec_str = self._get_field(fields, field_map, 'lat_seconds')
            
            lon_deg_str = self._get_field(fields, field_map, 'lon_degrees')
            lon_min_str = self._get_field(fields, field_map, 'lon_minutes')
            lon_sec_str = self._get_field(fields, field_map, 'lon_seconds')
            
            # Parse to numbers
            lat_deg = int(lat_deg_str) if lat_deg_str else 0
            lat_min = int(lat_min_str) if lat_min_str else 0
            lat_sec = float(lat_sec_str) if lat_sec_str else 0
            
            lon_deg = int(lon_deg_str) if lon_deg_str else 0
            lon_min = int(lon_min_str) if lon_min_str else 0
            lon_sec = float(lon_sec_str) if lon_sec_str else 0
            
            # Convert to decimal degrees
            lat = lat_deg + lat_min/60 + lat_sec/3600
            lon = -(lon_deg + lon_min/60 + lon_sec/3600)  # West is negative
            
            # Validate reasonable coordinates (US territory)
            if lat < 18 or lat > 72 or lon < -180 or lon > -60:
                return None, None
                
            return lat, lon
        except (ValueError, IndexError):
            return None, None

def main():
    """Test the parser with sample data."""
    fetcher = FCCDataFetcher()
    
    # Fetch a few FM stations to test
    print("Testing FM parser...")
    fm_stations = fetcher.fetch_fm_stations()
    
    if fm_stations:
        print(f"\nFirst 3 FM stations:")
        for station in fm_stations[:3]:
            print(f"  {station.call_sign} - {station.frequency} MHz - {station.city}, {station.state}")
    
    # Fetch a few AM stations to test
    print("\nTesting AM parser...")
    am_stations = fetcher.fetch_am_stations()
    
    if am_stations:
        print(f"\nFirst 3 AM stations:")
        for station in am_stations[:3]:
            print(f"  {station.call_sign} - {station.frequency:.3f} MHz - {station.city}, {station.state}")

if __name__ == "__main__":
    main()