import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
EXPECTED_STREET_NAMES = ["Avenue", "Boulevard", "Centre", "Close", "Court", "Crescent", "Diversion", "Drive", "East",
                         "Forest", "Gate", "Grove", "Highway", "Kingsway", "Lane", "Mall", "Mews", "North", "Parkway",
                         "Place", "Road", "South", "Street", "Terrace", "Trail", "Way", "West", "Wynd", "Broadway",
                         "Tsawwassen", "Walk", "Park", "Alley"]
EXPECTED_PROVINCE_NAMES = ["BC", "British Columbia", "british columbia", "bc", "British columbia", "Bc"]
EXPECTED_COUNTRY_NAMES = ["CA", "Canada", "Ca", "ca", "canada"]
STREET_NAME_MAPPING = { "Ave" : "Avenue",
                        "ave" : "Avenue",
                        "Ave." : "Avenue",
                        "av" : "Avenue",
                        "Commercial" : "Commercial Drive",
                        "Cornwall" : "Cornwall Avenue",
                        "Davie" : "Davie Street",
                        "St" : "Street",
                        "St." : "Street",
                        "street" : "Street",
                        "st" : "Street",
                        "ST." : "Street",
                        "Streettt" : "Street",
                        "Dunbar" : "Dunbar Street",
                        "Hwy" : "Highway",
                        "Hwy." : "Highway",
                        "Highway'" : "Highway",
                        "Granville" : "Granville Street",
                        "Hamilton" : "Hamilton Street",
                        "Dr" : "Drive",
                        "Dr." : "Drive",
                        "drive" : "Drive",
                        "Duranleau" : "Duranleau Street",
                        "Hastings" : "Hastings Street",
                        "Edmonds" : "Edmonds Street",
                        "Fir" : "Fir Street",
                        "Main" : "Main Street",
                        "Blvd" : "Boulevard",
                        "Blvd." : "Boulevard",
                        "Rd" : "Road",
                        "Rd." : "Road",
                        "RD" : "Road",
                        "Road," : "Road",
                        "Pl" : "Place",
                        "Pl." : "Place",
                        "W" : "West",
                        "W." : "West",
                        "E" : "East",
                        "E." : "East",
                        "S." : "South",
                        "S" : "South",
                        "N." : "North",
                        "N" : "North",
                        "Burrard" : "Burrard Street",
                        "Cambie" : "Cambie Street",
                        "Carrall" : "Carrall Street",
                        "Homer" : "Homer Street",
                        "Hornby" : "Hornby Street",
                        "Keefer" : "Keefer Street",
                        "Kootenay" : "Kootenay Street",
                        "Lougheed" : "Lougheed Highway",
                        "Mainland" : "Mainland Street",
                        "Manitoba" : "Manitoba Street",
                        "Cres" : "Crescent",
                        "Moncton" : "Moncton Street",
                        "Oak" : "Oak Street",
                        "Powell" : "Powell Street",
                        "Quebec" : "Quebec Street",
                        "Sanders" : "Sanders Street",
                        "Venables" : "Venables Street",
                        "Victoria" : "Victoria Drive",
                        "Pender" : "Pender Street",
                        "Willingdon" : "Willingdon Avenue",
                        "Yukon" : "Yukon Street"
                        }
SPECIFIC_STREET_NAME_MAPPING = { "ing George Hwy." : "King George Highway",
                                 "Mast Tower" : "Mast Tower Lane",
                                 "e Broadway" : "East Broadway",
                                 "41st Ave. W" : "41st Avenue West",
                                 "Hastings St E" : "Hastings Street East"
                                 }
SPECIFIC_HOUSENUMBER_MAPPING = { "201 City Square, 555" : ("555", "201 City Square"),
                                 "3917, Army, Navy, & Airforce Veterans Club, Taurus Unit #298" : (None, "3917 Army, Navy, & Airforce Veterans Club, Taurus Unit #298")
                                 }

# Files
osm_file = './vancouver.osm/vancouver_sample.osm'
json_file = './vancouver.osm/vancouver_sample.osm.json'
osm_file_full = './vancouver.osm/vancouver.osm'
json_file_full = './vancouver.osm/vancouver.osm.json'

# Regex patterns
lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
numbers = re.compile(r'^[0-9]+$')
pcode_match = re.compile(r'^V[0-9][A-Z] [0-9][A-Z][0-9]$')
pcode_relaxed_match = re.compile(r'^V[0-9][A-Z]\s?[0-9][A-Z][0-9]$')
lower_first = re.compile(r'^([a-z])')
street_ending = re.compile(r'(\S)+$')
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
contains_numbers = re.compile(r'([0-9]+)')

# Function that cleans osm json file and outputs a clean version of json
def clean_json(file_in, pretty = False):
    # Open file for cleaned json
    file_out = file_in[:len(file_in)-9]+"_cleaned"+file_in[len(file_in)-9:]
    with codecs.open(file_out, "w") as fw:
        # Read dirty json file
        with open(file_in, "r") as fr:
            for obj in fr:
                # Load dirty json object as dictionary
                record = json.loads(obj)
                # Clean dictionary object
                write_record = True
                # Check if dictionary object has address before cleaning
                if 'address' in record:      
                    # Clean address.postcode
                    if 'postcode' in record['address']:
                        # Remove if postal code is not Canadian
                        m = pcode_relaxed_match.search(record['address']['postcode'])
                        if m:
                            # Clean postal code if necessary
                            m = pcode_match.search(record['address']['postcode'])
                            if not m:
                                record['address']['postcode'] = clean_postcode(record['address']['postcode'])
                        else:
                            # Remove record
                            write_record = False                          
                    # Clean address.state
                    if 'state' in record['address']:
                        # Check if state is an expected province name, otherwise remove
                        if record['address']['state'] in EXPECTED_PROVINCE_NAMES:
                            # Transfer state value over to address.province
                            record['address']['province'] = record['address'].pop('state', None)
                        else:
                            # Remove record
                            write_record = False
                    # Clean address.province
                    if 'province' in record['address']:
                        # Check if province is expected, otherwise remove
                        if record['address']['province'] in EXPECTED_PROVINCE_NAMES:
                            record['address']['province'] = 'British Columbia'
                        else:
                            # Remove record
                            write_record = False
                    else:
                        # If province is not set in record, add to record
                        if 'street' in record['address']:
                            record['address']['province'] = 'British Columbia'
                    # Clean address.country
                    if 'country' in record['address']:
                        # Check if country is expected, otherwise remove
                        if record['address']['country'] in EXPECTED_COUNTRY_NAMES:
                            record['address']['country'] = 'Canada'
                        else:
                            # Remove record
                            write_record = False
                    else:
                        # If country is not set in record, add to record
                        if 'street' in record['address']:
                            record['address']['country'] = 'Canada'
                    # Clean address.city
                    if 'city' in record['address']:
                        # Check that city and province was not merged together
                        city_split = record['address']['city'].split(',')
                        if(len(city_split) > 1):
                            # Check if province merged is expected.  If not, remove record.
                            if city_split[1].replace(' ', '') in EXPECTED_PROVINCE_NAMES:
                                # Clean city value
                                record['address']['city'] = city_split[0].strip()
                            else:
                                # Remove record
                                write_record = False
                        # Check that city is not in lowercase
                        m = lower.search(record['address']['city'])
                        if m:
                            # Capitalize city name
                            record['address']['city'] = record['address']['city'].capitalize()
                    # Clean address.housename
                    if 'housename' in record['address']:
                        # Clean record if it contains numbers, otherwise leave alone
                        m = contains_numbers.search(record['address']['housename'])
                        if m:
                            # Get value of possible house number of unit
                            housenumber = m.group()
                            # If record doesn't already contain a house number, use value instead.
                            if 'housenumber' not in record['address']:
                                record['address']['housenumber'] = housenumber
                            else:
                                # If house name is found in house number already, don't need to do anything more
                                if housenumber in record['address']['housenumber']:
                                    pass
                                else:
                                    # If house name isn't found in house number, append it to house number
                                    record['address']['housenumber'] = record['address']['housenumber']+', '+record['address']['housename']
                            # Remove housename key from record to prevent redundancy
                            record['address'].pop('housename', None)
                    # Clean address.housenumber
                    if 'housenumber' in record['address']:
                        # Check if housenumber contains unexpected characters
                        try:
                            record['address']['housenumber'].decode()
                        except UnicodeEncodeError:
                            record['address']['housenumber'] = clean_housenumber(record['address']['housenumber'])
                        # Trim whitespaces from beginning and end of housenumber
                        record['address']['housenumber'] = record['address']['housenumber'].lstrip()
                        record['address']['housenumber'] = record['address']['housenumber'].rstrip()
                        # Clean housenumber if it is not a straightforward number
                        m = numbers.search(record['address']['housenumber'])
                        if not m:
                            # Extract unit from housenumber if applicable
                            unit, hn = extract_unit_housenumber(record['address']['housenumber'])
                            if((unit != None) and ('unit' not in record['address'])):
                                # Add unit value to address
                                record['address']['unit'] = unit
                                print("Unit: "+unit)
                            # Update housenumber value with cleaned value
                            record['address']['housenumber'] = hn
                            print("Housenumber: "+hn)
                            # Updating with very specific case manually
                            if(record['address']['housenumber'] == '205 East 10th Ave'):
                                record['address']['housenumber'] = '205'
                                record['address']['street'] = 'East 10th Avenue'
                    # Clean address.street
                    if 'street' in record['address']:
                        # Fix specific cases manually, where it is too unique a case to solve programmatically
                        if record['address']['street'] in SPECIFIC_STREET_NAME_MAPPING:
                            record['address']['street'] = SPECIFIC_STREET_NAME_MAPPING[record['address']['street']]
                        else: 
                            # Check if street uses a different form (ie. Ave instead of Avenue)
                            m = street_type_re.search(record['address']['street'])
                            if m:
                                ending = m.group()
                                if ending not in EXPECTED_STREET_NAMES:
                                    record['address']['street'] = update_street_name(record['address']['street'], STREET_NAME_MAPPING)
                    # Clean address.unit
                    if 'unit' in record['address']:
                        # Check if unit value contains "suite"
                        if "suite" in record['address']['unit'].lower():
                            # Remove suite from number
                            record['address']['unit'] = record['address']['unit'].replace('Suite', '')
                            record['address']['unit'] = record['address']['unit'].replace('suite', '')
                            # Trim off whitespaces from both sides
                            record['address']['unit'] = record['address']['unit'].lstrip()
                            record['address']['unit'] = record['address']['unit'].rstrip()
                            
                # Write cleaned dictionary to new json file
                if write_record:
                    if pretty:
                            fw.write(json.dumps(record, indent=2)+"\n")
                    else:
                        fw.write(json.dumps(record) + "\n")

# Extract unit from housenumber
# Function will try to recognize a pattern in the housenumber and extract the unit and housenumber from it
# If function cannot match a pattern, it will return None for unit and the original housenumber value for housenumber
def extract_unit_housenumber(s):
    print "================"
    print "Attempting to match: "+s
    # Match for formatting where the unit is placed in front of the housenumber (such as #101-7885)
    p1 = re.compile(r'^#([0-9]{1,5}[A-Za-z]{0,3})[\-\s\,]{1,3}([0-9]+)$')
    m = p1.search(s)
    if m:
        print "MATCHED by P1: "+s
        return (m.group(1), m.group(2))
    # Match for formatting where the unit is labeled as "Suite" after the housenumber with comma-separation (such as 10153, Suite 147-2153)
    p2 = re.compile(r'^([0-9]+)\, suite #?([0-9A-Za-z\-\s]+)$', re.IGNORECASE)
    m = p2.search(s)
    if m:
        print "MATCHED by P2: "+s
        return (m.group(2), m.group(1))
    # Match for formatting where the unit is labeled with "#" after the housenumber with comma-separation (such as 4269, #4051)
    p3 = re.compile(r'^([0-9]+)\, #([0-9\-]+)$')
    m = p3.search(s)
    if m:
        print "MATCHED by P3: "+s
        return (m.group(2), m.group(1))
    # Match for formatting similar to U1 601
    p4 = re.compile(r'^([A-Za-z]{1,3}[0-9]{1,5}|[0-9]{1,5}[A-Za-z]{1,3})[\-\s\,]{1,3}([0-9]+)$')
    m = p4.search(s)
    if m:
        print "MATCHED by P4: "+s
        return (m.group(1), m.group(2))
    # Match for formatting similar to Suite 110, 1333
    p5 = re.compile(r'^suite #?([0-9]{1,5}[A-Za-z]{0,3})[\-\s\,]{1,3}([0-9]+)$', re.IGNORECASE)
    m = p5.search(s)
    if m:
        print "MATCHED by P5: "+s
        return (m.group(1), m.group(2))
    # Match for formatting similar to Unit 102 -1626
    p6 = re.compile(r'^unit\:? #?([0-9]{1,5}[A-Za-z]{0,3})[\-\s\,]{1,3}([0-9]+)$', re.IGNORECASE)
    m = p6.search(s)
    if m:
        print "MATCHED by P6: "+s
        return (m.group(1), m.group(2))
    # Match for formatting similar to Studio 100 1000
    p7 = re.compile(r'^studio #?([0-9]{1,5}[A-Za-z]{0,3})[\-\s\,]{1,3}([0-9]+)$', re.IGNORECASE)
    m = p7.search(s)
    if m:
        print "MATCHED by P7: "+s
        return (m.group(1), m.group(2))
    # Match for formatting similar to 1238 #4
    p8 = re.compile(r'^([0-9]+)\,? #([0-9A-Za-z\-\s]+)$', re.IGNORECASE)
    m = p8.search(s)
    if m:
        print "MATCHED by P8: "+s
        return (m.group(2), m.group(1))
    # Match for ambiguous formats, but will assume that the shorter of the two strings is unit
    # If both strings are equal in length, it is too ambiguous to extract
    p9 = re.compile(r'^([0-9]+)[\-\s\,]{1,3}([0-9]+)$')
    m = p9.search(s)
    if m:
        # Check if there is any difference in length
        if(len(m.group(1)) < len(m.group(2))):  
            print "MATCHED by P9: "+s
            return (m.group(1), m.group(2))
        elif(len(m.group(1)) > len(m.group(2))):
            print "MATCHED by P9: "+s
            return (m.group(2), m.group(1))
    # Some cases needed to be manually mapped because they were too unique
    if s in SPECIFIC_HOUSENUMBER_MAPPING:
        print "MATCHED by MAPPING: "+s
        return SPECIFIC_HOUSENUMBER_MAPPING[s]
    # If we made it here, then no patterns were recognized, so just return original 
    print "COULD NOT RECOGNIZE PATTERN: "+s
    # Do basic cleaning of housenumber for consistency
    s = s.replace(';', '-')
    s = s.replace(' - ', '-')
    s = s.replace(', ', '-')
    s = s.replace(':', '')
    s = s.replace(',', '-')
    return (None, s)
    
# Returns a better street name for given street name
def update_street_name(name, mapping):
    # Get street type from name
    m = street_type_re.search(name)
    if m:
        street_type = m.group()
        # Replace street type with better one
        if street_type in mapping:
            name = name.replace(street_type, mapping[street_type])
    return name

# Cleans housenumber string
def clean_housenumber(s):
    text = ''
    # Remove unexpected characters from string
    for c in s:
        # Only include expected characters
        if(ord(c) < 128):
            # Append to text
            text += c
    # Remove extra spaces
    text = re.sub('\s{2,}', ' ', text)
    return text
    
# Cleans postal code format
def clean_postcode(old_pcode):
    if(len(old_pcode) == 6):
        new_pcode = old_pcode[:3]+' '+old_pcode[3:]
        return new_pcode
    else:
        print 'Error occurred in clean_pcode(): pcode string length does not match 6 characters' 
        return False

def main():
    # clean_json(json_file)
    clean_json(json_file_full)

if __name__ == "__main__":
    main()
