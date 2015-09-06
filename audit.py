import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json

'''
Example: JSON output
{
"_id": "2034989849",
"visible": "true",
"created": {
	"version":"2",
	"changeset:":"65454546",
	"timestamp":"2013-08-03T16:43:42Z",
	"user":"abcuser123",
	"uid":"1235454"
	},
"pos": [41.4394593, -54.234983],
"address": {
	"housenumber":"5157",
	"postcode":"60625",
	"street":"North Lincoln Ave."
	},
"amenity":"restaurant",
"cuisine":"mexican",
"name":"La Cabana De Don Luis",
"phone":"1 (773)-271-5176"
}
'''

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
EXPECTED_STREET_NAMES = ["Avenue", "Boulevard", "Centre", "Close", "Court", "Crescent", "Diversion", "Drive", "East",
                         "Forest", "Gate", "Grove", "Highway", "Kingsway", "Lane", "Mall", "Mews", "North", "Parkway",
                         "Place", "Road", "South", "Street", "Terrace", "Trail", "Way", "West", "Wynd", "Broadway",
                         "Tsawwassen", "Walk", "Park", "Alley"]

# Files
osm_file = './vancouver.osm/vancouver_sample.osm'
json_file = './vancouver.osm/vancouver_sample.osm.json'
clean_json_file = './vancouver.osm/vancouver_sample_cleaned.osm.json'
osm_file_full = './vancouver.osm/vancouver.osm'
json_file_full = './vancouver.osm/vancouver.osm.json'
clean_json_file_full = './vancouver.osm/vancouver_cleaned.osm.json'

# Regex patterns
lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
numbers = re.compile(r'^[0-9]+$')
pcode_match = re.compile(r'^V[0-9][A-Z] [0-9][A-Z][0-9]$')
lower_first = re.compile(r'^([a-z])')
street_ending = re.compile(r'(\S)+$')
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
contains_numbers = re.compile(r'([0-9]+)')

# Shape OSM data into desired data model in JSON
def shape_element(element):
    node = {}
    if element.tag == "node" or element.tag == "way" :
        # Process element attributes 
        node['type'] = element.tag
        if 'id' in element.attrib:
            node['id'] = element.attrib['id']
        if 'visible' in element.attrib:
            node['visible'] = element.attrib['visible']
        if ('lat' in element.attrib) & ('lon' in element.attrib):
            node['pos'] = [float(element.attrib['lat']), float(element.attrib['lon'])]
        # Process created attributes
        node['created'] = {}
        for c in CREATED:
            if c in element.attrib:
                node['created'][c] = element.attrib[c]
        # Process tags
        for tag in element.iter():
            # Check if tag is a <tag>
            if tag.tag == 'tag':
                # Check for problematic characters
                m1 = problemchars.search(tag.attrib['k'])
                if not m1:
                    # Check if contains proper colon structure
                    m2 = lower_colon.search(tag.attrib['k'])
                    if m2:
                        matched = m2.group(0)
                        # Split matched by colon
                        matched_split = matched.split(':')
                        # Check if address tag
                        if(matched_split[0] == 'addr'):
                            # Check if address dictionary already created in node
                            if 'address' not in node:
                                node['address'] = {}
                            # Address tag to address dictionary
                            node['address'][matched_split[1]] = tag.attrib['v']
                        else: 
                            # Add as normal tag
                            node[matched] = tag.attrib['v']
                    else:
                        # Check if contains a proper lowercase structure
                        m3 = lower.search(tag.attrib['k'])
                        if m3:
                            matched = m3.group(0)
                            # Check if the key is "type".  If so, rename the key so that it doesn't overwrite our node['type'] value.
                            if(matched != "type"):
                                # Add as normal tag
                                node[matched] = tag.attrib['v']
                            else:
                                node[matched+"_tag"] = tag.attrib['v']
            # Check if tag is a <nd>
            if tag.tag == 'nd':
                # Create list for node_refs if doesn't already exist
                if 'node_refs' not in node:
                    node['node_refs'] = []
                # Add id to list
                node['node_refs'].append(tag.attrib['ref'])
            
        # pprint.pprint(node)
        
        return node
    else:
        return None

# Iteratively parses OSM file, uses shape_element function to get data model and writes it to a JSON file
def process_map(file_in, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data

# Gets a dictionary of tags in the OSM and how many instances of the tag is used in the file
def audit_xml(filename):
    data = {}
    # Loop through data using iterative parser
    for event, elem in ET.iterparse(filename):
        # Check if tag is already a key in dictionary
        if elem.tag in data:
            data[elem.tag]['count'] += 1
        else:
            data[elem.tag] = {'count':1, 'attributes':set()}
        # Capture unique attributes
        for k,v in elem.attrib.iteritems():
            data[elem.tag]['attributes'].add(k)
        # Clear element out of memory
        elem.clear()
    return data

# Helper function for experimenting
def experiments(filename):
    data = set()
    with open(filename, "r") as f:
        for line in f:
            record = json.loads(line)
            if "address" in record:
                if "street" not in record['address']:
                    if record['type'] == 'way':
                        pprint.pprint(record['address'])

# Get a list of all keys used in json data model
def audit_json_keys(filename):
    data = set()
    with open(filename, "r") as f:
        for line in f:
            record = json.loads(line)
            for key in record.keys():
                data.add(key)
    return data

# Displays a JSON file in pretty format
def print_json(filename, records=10):
    data = []
    counter = 0
    with open(filename, "r") as f:
        for line in f:
            # Append row to data
            if(counter < records):
                data.append(json.loads(line))
            else:
                break
            # If arg is 0, do not increment counter
            if(records != 0):
                counter += 1
    # Display data
    pprint.pprint(data)

# Look up a record for a specific value of an address field
def lookup_address_record(filename, field, value):
    data = []
    # Regex pattern
    match_value = re.compile(r'('+value+')')
    with open(filename, "r") as f:
        for line in f:
            record = json.loads(line)
            if 'address' in record:
                if field in record['address']:
                    m = match_value.search(record['address'][field])
                    if m:
                        data.append(record)
    return data
        
# Provides an audit of the created_by field 
def audit_created_by(filename):
    data = {}
    counter = 0
    total = 0
    values = set()
    types = set()
    with open(filename, "r") as f:
        for line in f:
            record = json.loads(line)
            # Count total
            total += 1
            if 'created_by' in record:
                # Increment counter
                counter += 1
                # Record details
                values.add(record['created_by'])
                types.add(record['type'])
        # Shape data
        data[counter] = values
        data['total'] = total
        data['types'] = types
    # Return data
    return data

# Provides an audit of other fields and checks for empty values
def audit_other_fields_unexpected(filename):
    data = {}
    count = 0
    cases = []
    with open(filename, "r") as f:
        for line in f:
            record = json.loads(line)
            for key in record.keys():
                # Check for empty value
                if((record[key] == '') | (record[key] == 'NULL') | (record[key] == None)):
                    count += 1
                    cases.append(record)
    # Shape data
    data['count'] = count
    data['cases'] = cases
    # Return data
    return data

# Provides an audit of the address fields
def audit_address(filename):
    
    data = {}
    counter = 0
    total = 0
    attributes = set()
    cities = set()
    cities_counter = 0
    countries = set()
    countries_counter = 0
    pcode = set()
    pcode_counter = 0
    provinces = set()
    provinces_counter = 0
    states = set()
    states_counter = 0
    # address.street field
    streets = set()
    streets_counter = 0
    # address.unit field
    units = set()
    units_counter = 0
    # address.housename field
    housenames = set()
    housenames_counter = 0
    # address.housenumber field
    housenumbers = set()
    housenumbers_counter = 0
    
    with open(filename, "r") as f:
        for line in f:
            record = json.loads(line)
            # Count total
            total += 1
            if 'address' in record:
                # Increment counter
                counter += 1
                # Record different attributes
                for key in record['address'].keys():
                    attributes.add(key)
                # Display details about cities
                if 'city' in record['address']:
                    cities_counter += 1
                    cities.add(record['address']['city'])
                # Display details about countries
                if 'country' in record['address']:
                    countries_counter += 1
                    countries.add(record['address']['country'])
                # Display details about postcode
                if 'postcode' in record['address']:
                    pcode_counter += 1
                    # Record postal codes that are not expected
                    m = pcode_match.search(record['address']['postcode'])
                    if not m:
                        pcode.add(record['address']['postcode'])
                # Display details about province
                if 'province' in record['address']:
                    provinces_counter += 1
                    provinces.add(record['address']['province'])
                # Display details about state
                if 'state' in record['address']:
                    states_counter += 1
                    states.add(record['address']['state'])   
                # Display details about street ending variations
                if 'street' in record['address']:
                    streets_counter += 1
                    m = street_ending.search(record['address']['street'])
                    if m:
                        ending = m.group()
                        streets.add(ending)
                # Display details about unit
                if 'unit' in record['address']:
                    units_counter += 1
                    units.add(record['address']['unit'])
                # Display details about housename
                if 'housename' in record['address']:
                    housenames_counter += 1
                    housenames.add(record['address']['housename'])
                    # Print if contains numbers
                    m = contains_numbers.search(record['address']['housename'])
                    if m:
                        # pprint.pprint(record)
                        pass
                # Display details about housenumber
                if 'housenumber' in record['address']:
                    housenumbers_counter += 1
                    housenumbers.add(record['address']['housenumber'])

                # Display address
                # pprint.pprint(record['address'])
                
        # Shape data
        data['counter'] = counter
        data['total'] = total
        data['attributes'] = attributes
        data['cities'] = {'count':cities_counter, 'uniques':cities}
        data['countries'] = {'count':countries_counter, 'uniques':countries}
        data['postcodes'] = {'count':pcode_counter, 'unexpected':pcode}
        data['provinces'] = {'count':provinces_counter, 'uniques':provinces}
        data['states'] = {'count':states_counter, 'uniques':states}
        data['streets'] = {'count':streets_counter, 'uniques':streets}
        data['units'] = {'count':units_counter, 'uniques':units}
        data['housenames'] = {'count':housenames_counter, 'uniques':housenames}
        data['housenumbers'] = {'count':housenumbers_counter, 'uniques':housenumbers}
        
    # Return data
    return data

# Displays unexpected records in the address fields
def audit_address_unexpected(filename):
    
    data = {}
    # General variables
    counter = 0
    total = 0
    attributes = set()
    # address.city field
    cities = set()
    cities_counter = 0
    # address.country field
    countries = set()
    countries_counter = 0
    # address.postcode field
    pcode = set()
    pcode_counter = 0
    # address.province field
    provinces = set()
    provinces_counter = 0
    # address.state field
    states = set()
    states_counter = 0
    # address.street field
    streets = set()
    streets_counter = 0
    # address.unit field
    units = set()
    units_counter = 0
    # address.housename field
    housenames = []
    housenames_counter = 0
    # address.housenumber field
    housenumbers = set()
    housenumbers_counter = 0
    
    with open(filename, "r") as f:
        for line in f:
            record = json.loads(line)
            # Count total
            total += 1
            if 'address' in record:
                # Record how many records have addresses
                counter += 1
                # Record attributes found in address field
                for key in record['address'].keys():
                    attributes.add(key)
                # Display details about cities
                if 'city' in record['address']:
                    # Capture cities that have a comma-separated, therefore could be including a province
                    if ',' in record['address']['city']:
                        cities.add(record['address']['city'])
                        cities_counter += 1
                    # Capture cities that are lowercase 
                    m = lower.search(record['address']['city'])
                    if m:
                        cities.add(record['address']['city'])
                        cities_counter += 1
                # Display details about countries
                if 'country' in record['address']:
                    # Capture countries that do not have a country field 'Canada'
                    if(record['address']['country'] != 'Canada'):
                        countries_counter += 1
                        countries.add(record['address']['country'])
                else:
                    # Capture records that do not have a country field
                    countries_counter += 1
                    countries.add('')
                # Display details about postcode
                if 'postcode' in record['address']:
                    # Record postal codes that are not expected
                    m = pcode_match.search(record['address']['postcode'])
                    if not m:
                        pcode.add(record['address']['postcode'])
                        pcode_counter += 1
                # Display details about province
                if 'province' in record['address']:
                    # Capture records where province is not 'British Columbia'
                    if(record['address']['province'] != 'British Columbia'):
                        provinces_counter += 1
                        provinces.add(record['address']['province'])
                else:
                    # Capture records that do not have a province field
                    provinces_counter += 1
                    provinces.add('')
                # Display details about state
                if 'state' in record['address']:
                    # Capture records where state is used instead of province
                    states_counter += 1
                    states.add(record['address']['state'])   
                # Display details about street
                if 'street' in record['address']:
                    # Capture record if street is not capitalized
                    m = lower_first.search(record['address']['street'])
                    if m:
                        streets_counter += 1
                        streets.add(record['address']['street'])
                    # Capture record if street ending does not match expected
                    m = street_type_re.search(record['address']['street'])
                    if m:
                        ending = m.group()
                        if ending not in EXPECTED_STREET_NAMES:
                            streets_counter += 1
                            streets.add(record['address']['street'])
                # Display details about unit
                if 'unit' in record['address']:
                    # Capture record if "Suite" or "suite" is included in the unit number
                    if "suite" in record['address']['unit'].lower():
                        units_counter += 1
                        units.add(record['address']['unit'])
                # Display details about housename
                if 'housename' in record['address']:
                    # Capture record if it contains numbers (could be misused instead of address.housenumber)
                    m = contains_numbers.search(record['address']['housename'])
                    if m:
                        housenames_counter += 1
                        housenames.append(record['address'])
                # Display details about housenumber
                if 'housenumber' in record['address']:
                    # Capture record if housenumber has unexpected characters
                    try:
                        record['address']['housenumber'].decode()
                    except UnicodeEncodeError:
                        housenumbers_counter += 1
                        housenumbers.add(record['address']['housenumber'])
                    # Capture record if housenumber is not a number
                    m = numbers.search(record['address']['housenumber'])
                    if not m:
                        housenumbers_counter += 1
                        housenumbers.add(record['address']['housenumber'])
                    
        # Shape data
        data['counter'] = counter
        data['total'] = total
        data['attributes'] = attributes
        data['cities'] = {'count':cities_counter, 'unexpected':cities}
        data['countries'] = {'count':countries_counter, 'unexpected':countries}
        data['postcodes'] = {'count':pcode_counter, 'unexpected':pcode}
        data['provinces'] = {'count':provinces_counter, 'unexpected':provinces}
        data['states'] = {'count':states_counter, 'unexpected':states}
        data['streets'] = {'count':streets_counter, 'unexpected':streets}
        data['units'] = {'count':units_counter, 'unexpected':units}
        data['housenames'] = {'count':housenames_counter, 'unexpected':housenames}
        data['housenumbers'] = {'count':housenumbers_counter, 'unexpected':housenumbers}
        
    # Return data
    return data
            
def main():
    # pprint.pprint(audit_xml(osm_file))
    # process_map(osm_file)
    # process_map(osm_file_full)
    # print_json(json_file)
    # audit_created_by(json_file)
    # pprint.pprint(audit_address(json_file))
    # pprint.pprint(audit_address(clean_json_file))
    # pprint.pprint(lookup_address_record(json_file, 'street', 'Wynd'))
    # pprint.pprint(audit_json_keys(json_file))
    # pprint.pprint(audit_other_fields_unexpected(json_file))
    # experiments(json_file)
    
    # pprint.pprint(audit_address_unexpected(json_file))
    # pprint.pprint(audit_address_unexpected(clean_json_file))
    pprint.pprint(audit_address_unexpected(clean_json_file_full))

if __name__ == "__main__":
    main()
