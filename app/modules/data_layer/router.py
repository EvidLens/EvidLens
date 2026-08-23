from app.modules.database import get_session as get_db
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from .service import fetch_price_trends, fetch_demand_signals, fetch_location_analytics
from .models import PriceTrend, DemandSignal, LocationMetric
from app.core.guards import require_module, consume_credits

router = APIRouter(tags=["Market Intel"])

# ===== ALL SECTORS FROM YOUR MODEL - 75 TOTAL =====
KENYA_SECTORS = [
    "Banks",
    "Microfinance Institutions",
    "Insurance & HMOs",
    "Fintechs & Mobile Money",
    "Capital Markets & Investment Banks",
    "SACCOs",
    "Retail - Supermarkets & Chains",
    "Retail - Wholesale & Distributors",
    "FMCG - Food & Beverage",
    "FMCG - Personal Care & Household",
    "Manufacturing - Food Processing",
    "Manufacturing - Textiles & Apparel",
    "Manufacturing - Construction Materials",
    "Manufacturing - Automotive & Assembly",
    "Manufacturing - Pharmaceuticals",
    "Manufacturing - Chemicals & Plastics",
    "Agribusiness - Crops & Farming",
    "Agribusiness - Livestock & Dairy",
    "Agribusiness - Horticulture & Flowers",
    "Agribusiness - Fisheries & Aquaculture",
    "Agribusiness - Agro-processing",
    "Telcos & ISPs",
    "Media & Broadcasting",
    "Advertising & Marketing Agencies",
    "PR & Communications",
    "Real Estate - Developers",
    "Real Estate - Agents & Brokers",
    "Real Estate - Property Management",
    "Construction & Infrastructure",
    "Architecture & Engineering",
    "Healthcare - Hospitals & Clinics",
    "Healthcare - Pharmacies",
    "Healthcare - Medical Devices & Pharma",
    "Education - Universities & Colleges",
    "Education - Primary & Secondary Schools",
    "Education - EdTech & Training",
    "Logistics & Transport",
    "E-Commerce & Marketplaces",
    "Hospitality - Hotels & Resorts",
    "Hospitality - Restaurants & QSR",
    "Tourism & Tour Operators",
    "Aviation & Airlines",
    "Maritime & Shipping",
    "Energy - Electricity Generation",
    "Energy - Oil & Gas",
    "Energy - Renewable & Solar",
    "Energy - Utilities & Water",
    "Mining & Minerals",
    "Government - National Ministries",
    "Government - County Governments",
    "Government - State Corporations",
    "Government - Regulatory Authorities",
    "Public Safety & Security",
    "Defense",
    "NGOs",
    "INGOs & UN Agencies",
    "Donors & Development Partners",
    "Foundations & Philanthropy",
    "Investors - PE & VC",
    "Investors - Angel & Family Offices",
    "Professional Services - Law",
    "Professional Services - Consulting",
    "Professional Services - Accounting & Audit",
    "Professional Services - HR & Recruitment",
    "ICT & Software Companies",
    "Data Centers & Cloud Services",
    "Digital Marketing & Creative",
    "Automotive - Dealerships",
    "Automotive - Parts & Aftermarket",
    "Automotive - Ride-hailing & Boda",
    "Gaming & Sports",
    "Entertainment & Events",
    "Beauty & Wellness",
    "Waste Management & Recycling",
    "Environmental & Climate Services"
]

KENYA_COUNTIES = [
    "Baringo","Bomet","Bungoma","Busia","Elgeyo-Marakwet","Embu","Garissa","Homa Bay","Isiolo",
    "Kajiado","Kakamega","Kericho","Kiambu","Kilifi","Kirinyaga","Kisii","Kisumu","Kitui",
    "Kwale","Laikipia","Lamu","Machakos","Makueni","Mandera","Marsabit","Meru","Migori",
    "Mombasa","Murang'a","Nairobi","Nakuru","Nandi","Narok","Nyamira","Nyandarua","Nyeri",
    "Samburu","Siaya","Taita-Taveta","Tana River","Tharaka-Nithi","Trans Nzoia","Turkana",
    "Uasin Gishu","Vihiga","Wajir","West Pokot"
]

KENYA_SUBCOUNTIES = {
    "Mombasa": ["Changamwe","Jomvu","Kisauni","Nyali","Likoni","Mvita"],
    "Kwale": ["Msambweni","Lunga Lunga","Matuga","Kinango"],
    "Kilifi": ["Kilifi North","Kilifi South","Kaloleni","Rabai","Ganze","Malindi","Magarini"],
    "Tana River": ["Garsen","Galole","Bura"],
    "Lamu": ["Lamu East","Lamu West"],
    "Taita-Taveta": ["Taveta","Wundanyi","Mwatate","Voi"],
    "Garissa": ["Garissa Township","Balambala","Lagdera","Dadaab","Fafi","Ijara"],
    "Wajir": ["Wajir North","Wajir East","Tarbaj","Wajir West","Eldas","Wajir South"],
    "Mandera": ["Mandera West","Banisa","Mandera North","Mandera East","Lafey","Kutulo"],
    "Marsabit": ["Moyale","North Horr","Saku","Laisamis"],
    "Isiolo": ["Isiolo North","Isiolo South","Garba Tulla"],
    "Meru": ["Imenti North","Imenti South","Central Imenti","Buuri","Tigania East","Tigania West","Igembe North","Igembe South","Igembe Central"],
    "Tharaka-Nithi": ["Nithi (Chuka/Igambang'ombe)","Maara","Tharaka"],
    "Embu": ["Manyatta","Runyenjes","Mbeere South (Gachoka)","Mbeere North (Siakago)"],
    "Kitui": ["Kitui Central","Kitui West","Kitui Rural","Kitui South","Mutomo","Mwingi North","Mwingi Central","Mwingi West"],
    "Machakos": ["Machakos Town","Mavoko","Kathiani","Matungulu","Kangundo","Mwala","Yatta","Masinga"],
    "Makueni": ["Makueni","Mbooni","Kibwezi West","Kibwezi East","Kaiti","Kilome"],
    "Nyandarua": ["Kinangop","Kipipiri","Ol Kalou","Ol Jorok","Ndaragwa"],
    "Nyeri": ["Nyeri Town","Tetu","Kieni","Mathira","Othaya","Mukurweini"],
    "Kirinyaga": ["Kirinyaga Central","Kirinyaga East (Gichugu)","Kirinyaga West (Ndia)","Mwea East","Mwea West"],
    "Murang'a": ["Kiharu","Kangema","Mathioya","Kigumo","Maragwa","Kandara","Gatanga"],
    "Kiambu": ["Thika Town","Ruiru","Githunguri","Kiambu","Kiambaa","Kabete","Kikuyu","Limuru","Lari","Gatundu South","Gatundu North","Juja"],
    "Turkana": ["Turkana Central","Turkana North","Turkana West","Turkana South","Turkana East","Loima"],
    "West Pokot": ["Kapenguria","Sigor","Kacheliba","Pokot South"],
    "Samburu": ["Samburu Central","Samburu North","Samburu East"],
    "Trans Nzoia": ["Saboti","Kiminini","Cherangany","Kwanza","Endebess"],
    "Uasin Gishu": ["Eldoret East","Eldoret West","Kesses","Moiben","Soy","Turbo"],
    "Elgeyo-Marakwet": ["Keiyo North","Keiyo South","Marakwet East","Marakwet West"],
    "Nandi": ["Nandi Hills","Emgwen","Chesumei","Aldai","Mosop","Nandi Central"],
    "Baringo": ["Baringo Central","Baringo North","Baringo South","Mogotio","Tiaty","Eldama Ravine"],
    "Laikipia": ["Laikipia East","Laikipia West","Laikipia North","Nyahururu","Ol Moran"],
    "Nakuru": ["Nakuru Town East","Nakuru Town West","Naivasha","Gilgil","Molo","Njoro","Kuresoi North","Kuresoi South","Rongai","Subukia"],
    "Narok": ["Narok North","Narok South","Narok East","Narok West","Transmara West","Transmara East"],
    "Kajiado": ["Kajiado Central","Kajiado North","Kajiado East","Kajiado West","Kajiado South"],
    "Kericho": ["Ainamoi","Belgut","Bureti","Kipkelion East","Kipkelion West","Soin/Sigowet"],
    "Bomet": ["Bomet Central","Bomet East","Chepalungu","Konoin","Sotik"],
    "Kakamega": ["Lurambi","Mumias East","Mumias West","Matungu","Navakholo","Khwisero","Butere","Shinyalu","Ikolomani","Lugari","Likuyani"],
    "Vihiga": ["Vihiga","Sabatia","Hamisi","Emuhaya","Luanda"],
    "Bungoma": ["Kanduyi","Bumula","Kabuchai","Kimilili","Mt. Elgon","Sirisia","Tongaren","Webuye East","Webuye West"],
    "Busia": ["Teso North","Teso South","Nambale","Matayos","Butula","Funyula","Budalangi"],
    "Siaya": ["Alego Usonga","Gem","Ugenya","Ugunja","Bondo","Rarieda"],
    "Kisumu": ["Kisumu Central","Kisumu East","Kisumu West","Seme","Nyando","Muhoroni","Nyakach"],
    "Homa Bay": ["Homa Bay Town","Kasipul","Kabondo Kasipul","Karachuonyo","Rangwe","Ndhiwa","Mbita","Suba"],
    "Migori": ["Migori East","Migori West","Rongo","Awendo","Uriri","Nyatike","Kuria East","Kuria West"],
    "Kisii": ["Kitutu Chache North","Kitutu Chache South","South Mugirango","Bomachoge Borabu","Bomachoge Chache","Bobasi","Nyaribari Chache","Nyaribari Masaba","Bonchari"],
    "Nyamira": ["West Mugirango","North Mugirango","Kitutu Masaba","Borabu"],
    "Nairobi": ["Westlands","Dagoretti North","Dagoretti South","Lang'ata","Kibra","Roysambu","Kasarani","Ruaraka","Embakasi North","Embakasi South","Embakasi East","Embakasi West","Embakasi Central","Makadara","Kamukunji","Starehe","Mathare"]
}

@router.get("/api/data/counties")
def api_get_counties():
    return {"counties": KENYA_COUNTIES}

@router.get("/api/data/sectors")
def api_get_sectors():
    return {"sectors": KENYA_SECTORS}

@router.get("/api/data/subcounties")
def api_get_subcounties(county: str = Query(...)):
    return {"subcounties": KENYA_SUBCOUNTIES.get(county, [])}

@router.get("/api/counties")
def legacy_counties():
    return {"counties": KENYA_COUNTIES}

@router.get("/api/sectors")
def legacy_sectors():
    return {"sectors": KENYA_SECTORS}

@router.get("/api/subcounties")
def legacy_subcounties(county: str = Query(...)):
    return {"subcounties": KENYA_SUBCOUNTIES.get(county, [])}

@router.get("/api/get_counties")
def legacy_get_counties():
    return {"counties": KENYA_COUNTIES}

@router.get("/api/get_sectors")
def legacy_get_sectors():
    return {"sectors": KENYA_SECTORS}

@router.get("/api/get_subcounties")
def legacy_get_subcounties(county: str = Query(...)):
    return {"subcounties": KENYA_SUBCOUNTIES.get(county, [])}
