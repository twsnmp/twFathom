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

    def test_environment_openweathermap(self):
        payload = '{"coord":{"lon":139.5577,"lat":35.8578},"weather":[{"id":804,"main":"Clouds","description":"overcast clouds","icon":"04n"}],"base":"stations","main":{"temp":11.86,"feels_like":11.35,"temp_min":11.65,"temp_max":12.79,"pressure":1020,"humidity":86,"sea_level":1020,"grnd_level":1014},"visibility":10000,"wind":{"speed":2.81,"deg":29,"gust":2.81},"clouds":{"all":100},"dt":1779476805,"sys":{"type":2,"id":2091017,"country":"JP","sunrise":1779478283,"sunset":1779529552},"timezone":32400,"id":1850144,"name":"Fujimi","cod":200}'
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'environment')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['temperature'], 11.86)
        self.assertEqual(results[0]['humidity'], 86.0)
        self.assertEqual(results[0]['pressure'], 1020.0)

class TestFileParsers(unittest.TestCase):
    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'test_data')

    def read_file(self, filename):
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def test_environment_json_single_file(self):
        payload = self.read_file('environment_single.json')
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'environment')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['timestamp'], '2026-05-23T04:00:00')
        self.assertEqual(results[0]['temperature'], 25.4)
        self.assertEqual(results[0]['humidity'], 60.2)
        self.assertEqual(results[0]['pressure'], 1011.5)
        self.assertEqual(results[0]['co2'], 520.0)
        self.assertEqual(results[0]['soil_moisture'], 28.1)
        self.assertEqual(results[0]['illuminance'], 350.5)

    def test_environment_json_multi_file(self):
        payload = self.read_file('environment_multi.json')
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'environment')
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['timestamp'], '2026-05-23T04:00:00')
        self.assertEqual(results[1]['timestamp'], '2026-05-23T04:01:00')
        self.assertEqual(results[2]['timestamp'], '2026-05-23T04:02:00')
        self.assertEqual(results[0]['temperature'], 25.4)
        self.assertEqual(results[1]['temperature'], 25.8)
        self.assertEqual(results[2]['temperature'], 26.1)

    def test_environment_csv_file(self):
        payload = self.read_file('environment.csv')
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'environment')
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]['timestamp'], '2026-05-23T04:00:00')
        self.assertEqual(results[1]['timestamp'], '2026-05-23T04:01:00')
        self.assertEqual(results[2]['timestamp'], '2026-05-23T04:02:00')
        self.assertEqual(results[3]['timestamp'], '2026-05-23T04:03:00')
        self.assertEqual(results[0]['temperature'], 22.5)
        self.assertEqual(results[0]['soil_moisture'], 30.5)
        self.assertEqual(results[0]['illuminance'], 120.0)
        self.assertEqual(results[1]['temperature'], 23.0)
        self.assertEqual(results[1]['soil_moisture'], 31.0)
        self.assertEqual(results[1]['illuminance'], 125.5)
        self.assertEqual(results[2]['temperature'], 23.5)
        self.assertEqual(results[3]['temperature'], 24.0)

    def test_traffic_json_list_file(self):
        payload = self.read_file('traffic_list.json')
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'traffic')
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['timestamp'], '2026-05-23T04:00:00')
        self.assertEqual(results[1]['timestamp'], '2026-05-23T04:01:00')
        self.assertEqual(results[2]['timestamp'], '2026-05-23T04:02:00')
        self.assertEqual(results[0]['rx_pps'], 100.0)
        self.assertEqual(results[0]['tx_pps'], 150.0)
        self.assertEqual(results[0]['rx_bps'], 80000.0)
        self.assertEqual(results[0]['tx_bps'], 120000.0)
        self.assertEqual(results[1]['rx_pps'], 110.0)
        self.assertEqual(results[2]['rx_pps'], 105.0)

    def test_traffic_csv_file(self):
        payload = self.read_file('traffic.csv')
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'traffic')
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]['timestamp'], '2026-05-23T04:00:00')
        self.assertEqual(results[1]['timestamp'], '2026-05-23T04:01:00')
        self.assertEqual(results[2]['timestamp'], '2026-05-23T04:02:00')
        self.assertEqual(results[3]['timestamp'], '2026-05-23T04:03:00')
        self.assertEqual(results[0]['rx_pps'], 100.0)
        self.assertEqual(results[1]['tx_pps'], 160.0)
        self.assertEqual(results[2]['rx_pps'], 105.0)
        self.assertEqual(results[3]['rx_pps'], 120.0)

    def test_environment_openweathermap_file(self):
        payload = self.read_file('environment_openweathermap.json')
        dtype, results = auto_parse_and_map(payload)
        
        self.assertEqual(dtype, 'environment')
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(results[0]['timestamp'])
        self.assertEqual(results[0]['temperature'], 11.86)
        self.assertEqual(results[0]['humidity'], 86.0)
        self.assertEqual(results[0]['pressure'], 1020.0)

if __name__ == '__main__':
    unittest.main()


