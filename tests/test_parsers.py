import sys
import os
import unittest

# Append the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from twfathom.parsers import auto_parse_and_map

class TestParsers(unittest.TestCase):
    def test_environment_json_single(self):
        payload = '{"temp": 25.4, "humidity": 60.2, "pressure": 1011.5, "co2": 520, "soil_moisture": 28.1, "lux": 350.5}'
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'environment')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['temperature'], 25.4)
        self.assertEqual(results[0]['humidity'], 60.2)
        self.assertEqual(results[0]['pressure'], 1011.5)
        self.assertEqual(results[0]['co2'], 520.0)
        self.assertEqual(results[0]['soil_moisture'], 28.1)
        self.assertEqual(results[0]['illuminance'], 350.5)
 
    def test_environment_csv(self):
        payload = "temp,humidity,pressure,co2,soil,illuminance\n22.5,50.1,1013.2,450,30.5,120.0\n23.0,51.0,1012.9,455,31.0,125.5"
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'environment')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['temperature'], 22.5)
        self.assertEqual(results[0]['soil_moisture'], 30.5)
        self.assertEqual(results[0]['illuminance'], 120.0)
        self.assertEqual(results[1]['temperature'], 23.0)
        self.assertEqual(results[1]['soil_moisture'], 31.0)
        self.assertEqual(results[1]['illuminance'], 125.5)

    def test_traffic_json_list(self):
        payload = '[{"rx_pps": 100, "tx_pps": 150, "rx_bps": 80000, "tx_bps": 120000}]'
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'traffic')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['rx_pps'], 100.0)
        self.assertEqual(results[0]['tx_pps'], 150.0)
        self.assertEqual(results[0]['rx_bps'], 80000.0)
        self.assertEqual(results[0]['tx_bps'], 120000.0)

    def test_traffic_csv(self):
        payload = "rx_pps,tx_pps,rx_bps,tx_bps\n100,150,80000,120000\n110,160,88000,130000"
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'traffic')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['rx_pps'], 100.0)
        self.assertEqual(results[1]['tx_pps'], 160.0)

if __name__ == '__main__':
    unittest.main()
