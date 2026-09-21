import sys, os
sys.path.insert(0, os.path.abspath("."))
from company_info.extractors.name_extractor import extract_person_name_from_headline, clean_person_name

headline = "Housing Heavy Hitter John O'Connor Parachuted Into Circle Amid Regulatory Concerns"
name = extract_person_name_from_headline(headline, "AHB")
print("Extracted name from headline:", name)

h2 = "Industry Veteran Jeremy Xu Appointed as CEO of ABF Ingredients"
name2 = extract_person_name_from_headline(h2, "ABF Ingredients")
print("Extracted name from h2:", name2)

h3 = "Glanbia appoints Wendy Chang Smith as Chief Financial Officer Designate"
name3 = extract_person_name_from_headline(h3, "Glanbia")
print("Extracted name from h3:", name3)
