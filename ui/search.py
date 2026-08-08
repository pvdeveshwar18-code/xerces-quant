"""
XERCES Search & Stock Universe Resolution Module
Contains 600+ NSE/BSE stocks across 18 sectors.
"""

import streamlit as st

SECTORS = {
    "🏦 Banking & Finance": [
        ("HDFC Bank","HDFCBANK"),("ICICI Bank","ICICIBANK"),("SBI","SBIN"),("Kotak Mahindra Bank","KOTAKBANK"),
        ("Axis Bank","AXISBANK"),("IndusInd Bank","INDUSINDBK"),("Bank of Baroda","BANKBARODA"),
        ("PNB","PNB"),("Canara Bank","CANBK"),("Union Bank","UNIONBANK"),("Bank of India","BANKINDIA"),
        ("Indian Bank","INDIANB"),("UCO Bank","UCOBANK"),("Central Bank","CENTRALBK"),("IOB","IOB"),
        ("Federal Bank","FEDERALBNK"),("RBL Bank","RBLBANK"),("Yes Bank","YESBANK"),
        ("IDFC First Bank","IDFCFIRSTB"),("Bandhan Bank","BANDHANBNK"),("AU Small Finance Bank","AUBANK"),
        ("Equitas Small Finance","EQUITASBNK"),("Ujjivan Small Finance","UJJIVANSFB"),
        ("City Union Bank","CUB"),("Karur Vysya Bank","KARURVYSYA"),("South Indian Bank","SOUTHBANK"),
        ("Dhanlaxmi Bank","DHANBANK"),("Karnataka Bank","KTKBANK"),
        ("Bajaj Finance","BAJFINANCE"),("Bajaj Finserv","BAJAJFINSV"),("Cholamandalam Finance","CHOLAFIN"),
        ("Muthoot Finance","MUTHOOTFIN"),("Manappuram Finance","MANAPPURAM"),("L&T Finance","LTF"),
        ("Shriram Finance","SHRIRAMFIN"),("Piramal Enterprises","PEL"),("HDFC AMC","HDFCAMC"),
        ("Nippon India AMC","NAM-INDIA"),("UTI AMC","UTIAMC"),("Aditya Birla AMC","ABSLAMC"),
        ("SBI Cards","SBICARD"),("SBI Life Insurance","SBILIFE"),("HDFC Life","HDFCLIFE"),
        ("LIC India","LICI"),("Star Health Insurance","STARHEALTH"),("New India Assurance","NIACL"),
        ("General Insurance Corp","GICRE"),("ICICI Prudential Life","ICICIPRULI"),
        ("ICICI Lombard","ICICIGI"),("Max Financial","MFSL"),("Five Star Business","FIVESTAR"),
        ("Aavas Financiers","AAVAS"),("Home First Finance","HOMEFIRST"),("Aptus Value Housing","APTUS"),
        ("Repco Home Finance","REPCOHOME"),("Can Fin Homes","CANFINHOME"),("LIC Housing Finance","LICHSGFIN"),
    ],
    "💻 IT & Technology": [
        ("TCS","TCS"),("Infosys","INFY"),("HCL Technologies","HCLTECH"),("Wipro","WIPRO"),
        ("Tech Mahindra","TECHM"),("LTIMindtree","LTIM"),("Mphasis","MPHASIS"),("Coforge","COFORGE"),
        ("Persistent Systems","PERSISTENT"),("L&T Technology","LTTS"),("Tata Elxsi","TATAELXSI"),
        ("KPIT Technologies","KPITTECH"),("Zensar Technologies","ZENSARTECH"),("Mastek","MASTEK"),
        ("Hexaware","HEXAWARE"),("Birlasoft","BSOFT"),("Intellect Design","INTELLECT"),
        ("Cyient","CYIENT"),("Sonata Software","SONATSOFTW"),("Happiest Minds","HAPPSTMNDS"),
        ("Tanla Platforms","TANLA"),("Firstsource Solutions","FSL"),("Newgen Software","NEWGEN"),
        ("Ramco Systems","RAMCOSYS"),("KFIN Technologies","KFINTECH"),("Angel One","ANGELONE"),
        ("Route Mobile","ROUTE"),("Nazara Technologies","NAZARA"),("Netweb Technologies","NETWEB"),
        ("Tata Communications","TATACOMM"),("Rategain Travel Tech","RATEGAIN"),("Zaggle Prepaid","ZAGGLE"),
        ("Majesco","MAJESCO"),("Saksoft","SAKSOFT"),("Nucleus Software","NUCLEUSSOFT"),
    ],
    "🏭 Industrials & Capital Goods": [
        ("Larsen & Toubro","LT"),("Siemens India","SIEMENS"),("ABB India","ABB"),("Bharat Electronics","BEL"),
        ("HAL","HAL"),("BEML","BEML"),("Thermax","THERMAX"),("Cummins India","CUMMINSIND"),
        ("Bharat Forge","BHARATFORG"),("Ramkrishna Forgings","RKFORGE"),("Escorts Kubota","ESCORTS"),
        ("Carborundum Universal","CARBORUNIV"),("AIA Engineering","AIAENG"),("Timken India","TIMKEN"),
        ("Schaeffler India","SCHAEFFLER"),("SKF India","SKFINDIA"),("Grindwell Norton","GRINDWELL"),
        ("Elgi Equipments","ELGIEQUIP"),("Kirloskar Brothers","KIRLOSBROS"),("KSB","KSB"),
        ("Voltamp Transformers","VOLTAMP"),("Sterling Wilson","SWSOLAR"),("Va Tech Wabag","WABAG"),
        ("NBCC","NBCC"),("NCC","NCC"),("KEC International","KEC"),("Kalpataru Projects","KPIL"),
        ("G R Infraprojects","GRINFRA"),("ITD Cementation","ITDCEM"),("PNC Infratech","PNCINFRA"),
        ("H.G. Infra","HGINFRA"),("Ashoka Buildcon","ASHOKA"),("IRB Infrastructure","IRB"),
        ("Ahluwalia Contracts","AHLUCONT"),("Dilip Buildcon","DBL"),("Rail Vikas Nigam","RVNL"),
        ("Texmaco Rail","TEXRAILWAG"),("Jupiter Wagons","JWL"),("Titagarh Rail","TITAGARH"),
        ("Mazagon Dock","MAZDOCK"),("Garden Reach Shipbuilders","GRSE"),("Cochin Shipyard","COCHINSHIP"),
    ],
    "⚡ Energy & Power": [
        ("Reliance Industries","RELIANCE"),("ONGC","ONGC"),("BPCL","BPCL"),("IOC","IOC"),
        ("HPCL","HPCL"),("GAIL India","GAIL"),("Petronet LNG","PETRONET"),("Castrol India","CASTROLIND"),
        ("NTPC","NTPC"),("Power Grid Corp","POWERGRID"),("Tata Power","TATAPOWER"),
        ("Adani Green","ADANIGREEN"),("Adani Enterprises","ADANIENT"),("JSW Energy","JSWENERGY"),
        ("Torrent Power","TORNTPOWER"),("NHPC","NHPC"),("SJVN","SJVN"),("CESC","CESC"),
        ("Inox Wind","INOXWIND"),("Suzlon Energy","SUZLON"),("IREDA","IREDA"),
        ("PFC","PFC"),("REC","RECLTD"),("IGL","IGL"),("Gujarat Gas","GUJGASLTD"),
        ("Adani Total Gas","ATGL"),("Mahanagar Gas","MGL"),("Reliance Power","RPOWER"),
        ("Jaiprakash Power","JPPOWER"),("CPCL","CPCL"),("Mangalore Refinery","MRPL"),
        ("Chennai Petroleum","CHENNPETRO"),("GIPCL","GIPCL"),("TANGEDCO","TNPL"),
        ("Greenko","GKLENERGY"),("Acme Solar","ACMESOLAR"),("Premier Energies","PREMIERENE"),
    ],
    "🚗 Auto & Auto Ancillaries": [
        ("Maruti Suzuki","MARUTI"),("Tata Motors","TATAMOTORS"),("M&M","M&M"),
        ("Bajaj Auto","BAJAJ-AUTO"),("Hero MotoCorp","HEROMOTOCO"),("Eicher Motors","EICHERMOT"),
        ("TVS Motor","TVSMOTOR"),("Ashok Leyland","ASHOKLEY"),("Force Motors","FORCEMOT"),
        ("Apollo Tyres","APOLLOTYRE"),("MRF","MRF"),("CEAT","CEATLTD"),
        ("Balkrishna Industries","BALKRISIND"),("Bosch India","BOSCHLTD"),("Motherson Sumi","MOTHERSON"),
        ("Minda Industries","MINDAIND"),("Minda Corp","MINDACORP"),("Suprajit Engineering","SUPRAJIT"),
        ("Endurance Technologies","ENDURANCE"),("Gabriel India","GABRIEL"),("Jamna Auto","JAMNAAUTO"),
        ("Sona BLW Precision","SONACOMS"),("Uno Minda","UNOMINDA"),("Fiem Industries","FIEMIND"),
        ("Sandhar Technologies","SANDHAR"),("Craftsman Automation","CRAFTSMAN"),
        ("Bharat Forge","BHARATFORG"),("Schaeffler India","SCHAEFFLER"),("Samvardhana Motherson","MOTHERSON"),
        ("Varroc Engineering","VARROC"),("Pricol","PRICOL"),("Lumax Industries","LUMAXIND"),
        ("Lumax Auto Technologies","LUMAXTECH"),("Spark Minda","MINDAIND"),("Automotive Axles","AUTOAXLES"),
    ],
    "💊 Pharma & Healthcare": [
        ("Sun Pharma","SUNPHARMA"),("Dr. Reddy's","DRREDDY"),("Cipla","CIPLA"),("Lupin","LUPIN"),
        ("Biocon","BIOCON"),("Alkem Labs","ALKEM"),("Torrent Pharma","TORNTPHARM"),
        ("Abbott India","ABBOTINDIA"),("Pfizer India","PFIZER"),("Sanofi India","SANOFI"),
        ("Divi's Laboratories","DIVISLAB"),("Aurobindo Pharma","AUROPHARMA"),("Zydus Lifesciences","ZYDUSLIFE"),
        ("Ipca Laboratories","IPCALAB"),("Natco Pharma","NATCOPHARM"),("Glenmark Pharma","GLENMARK"),
        ("Mankind Pharma","MANKIND"),("Ajanta Pharma","AJANTPHARM"),("JB Chemicals","JBCHEPHARM"),
        ("FDC Limited","FDC"),("Piramal Pharma","PPLPHARMA"),("Laurus Labs","LAURUSLABS"),
        ("Granules India","GRANULES"),("Aarti Drugs","AARTIDRUGS"),("Caplin Point","CAPLIPOINT"),
        ("Apollo Hospitals","APOLLOHOSP"),("Max Healthcare","MAXHEALTH"),("Fortis Healthcare","FORTIS"),
        ("Narayana Hrudayalaya","NH"),("Medanta","MEDANTA"),("HCG Oncology","HCG"),
        ("Vijaya Diagnostic","VIJAYA"),("Metropolis Healthcare","METROPOLIS"),
        ("Dr. Lal Path Labs","LALPATHLAB"),("Thyrocare","THYROCARE"),
        ("Sanofi India","SANOFI"),("Wockhardt","WOCKPHARMA"),("Strides Pharma","STAR"),
        ("Suven Life Sciences","SUVEN"),("Solara Active Pharma","SOLARA"),
    ],
    "🏗️ Metals & Mining": [
        ("Tata Steel","TATASTEEL"),("JSW Steel","JSWSTEEL"),("Hindalco","HINDALCO"),
        ("Vedanta","VEDL"),("Hindustan Zinc","HINDZINC"),("National Aluminium","NATIONALUM"),
        ("SAIL","SAIL"),("Coal India","COALINDIA"),("NMDC","NMDC"),("Jindal Steel","JINDALSTEL"),
        ("APL Apollo Tubes","APLAPOLLO"),("Ratnamani Metals","RATNAMANI"),
        ("Maharashtra Seamless","MAHSEAMLES"),("Welspun Corp","WELCORP"),("Shyam Metalics","SHYAMMETL"),
        ("Godawari Power","GPIL"),("GMDC","GMDC"),("MOIL","MOIL"),
        ("Hindustan Copper","HINDCOPPER"),("Tinplate Company","TINPLATE"),
        ("Jindal Stainless","JSL"),("JSPL","JINDALPOLY"),("Steel Authority","SAIL"),
        ("Tata Metaliks","TATAMETALI"),("Maithan Alloys","MAITHANALL"),
    ],
    "🧱 Cement & Construction": [
        ("UltraTech Cement","ULTRACEMCO"),("Shree Cement","SHREECEM"),("Ambuja Cements","AMBUJACEM"),
        ("ACC","ACC"),("JK Cement","JKCEMENT"),("Dalmia Bharat","DALBHARAT"),
        ("Ramco Cements","RAMCOCEM"),("Heidelberg Cement","HEIDELBERG"),("JK Lakshmi Cement","JKLAKSHMI"),
        ("Birla Corporation","BIRLACORPN"),("Orient Cement","ORIENTCEM"),("India Cements","INDIACEM"),
        ("Sagar Cements","SAGCEM"),("Star Cement","STARCEMENT"),("NCL Industries","NCLIND"),
        ("Prism Johnson","PRSMJOHNSN"),("Kajaria Ceramics","KAJARIACER"),("CERA Sanitary","CERA"),
        ("Astral","ASTRAL"),("Supreme Industries","SUPREMEIND"),("Finolex Industries","FINPIPE"),
        ("Somany Ceramics","SOMANYCERA"),("Cello World","CELLO"),("Polyplex Corp","POLYPLEX"),
    ],
    "🛒 FMCG & Consumer": [
        ("Hindustan Unilever","HINDUNILVR"),("ITC","ITC"),("Nestle India","NESTLEIND"),
        ("Britannia","BRITANNIA"),("Dabur India","DABUR"),("Godrej Consumer","GODREJCP"),
        ("Marico","MARICO"),("Emami","EMAMILTD"),("Bajaj Consumer","BAJAJCON"),
        ("Tata Consumer","TATACONSUM"),("Varun Beverages","VBL"),("Radico Khaitan","RADICO"),
        ("United Spirits","MCDOWELL-N"),("United Breweries","UBL"),("Jubilant FoodWorks","JUBLFOOD"),
        ("Westlife Foodworld","WESTLIFE"),("Burger King India","BURGERKING"),
        ("Devyani International","DEVYANI"),("Sapphire Foods","SAPPHIRE"),
        ("Mrs Bectors Food","BECTORFOOD"),("Heritage Foods","HERITGFOOD"),("Hatsun Agro","HATSUN"),
        ("Bikaji Foods","BIKAJI"),("P&G Hygiene","PGHH"),("Colgate Palmolive","COLPAL"),
        ("Kansai Nerolac","KANSAINER"),("Asian Paints","ASIANPAINT"),("Berger Paints","BERGEPAINT"),
        ("Indigo Paints","INDIGOPNTS"),("Pidilite","PIDILITIND"),("Prataap Snacks","PRATAAP"),
        ("DFM Foods","DFMFOODS"),("CCL Products","CCL"),
    ],
    "🛍️ Retail & E-Commerce": [
        ("Zomato","ZOMATO"),("Eternal (Zomato)","ETERNAL"),("Swiggy","SWIGGY"),("Paytm","PAYTM"),
        ("Nykaa","NYKAA"),("PB Fintech","POLICYBZR"),("Delhivery","DELHIVERY"),
        ("Info Edge (Naukri)","NAUKRI"),("IndiaMart","INDIAMART"),("Just Dial","JUSTDIAL"),
        ("Matrimony.com","MATRIMONY"),("CarTrade Tech","CARTRADE"),
        ("Avenue Supermarts (DMart)","DMART"),("Trent","TRENT"),("V-Mart Retail","VMART"),
        ("Bata India","BATAINDIA"),("Relaxo Footwear","RELAXO"),("Campus Activewear","CAMPUS"),
        ("Metro Brands","METROBRAND"),("Shoppers Stop","SHOPERSTOP"),("Titan Company","TITAN"),
        ("Kalyan Jewellers","KALYANKJIL"),("Senco Gold","SENCO"),("PC Jeweller","PCJEWELLER"),
        ("Thangamayil Jewellery","THANGAMAYL"),
    ],
    "✈️ Infrastructure & Logistics": [
        ("Adani Ports","ADANIPORTS"),("GMR Airports","GMRINFRA"),("IndiGo","INDIGO"),
        ("SpiceJet","SPICEJET"),("Blue Dart","BLUEDART"),("Container Corp","CONCOR"),
        ("Gateway Distriparks","GDL"),("Mahindra Logistics","MAHLOG"),("Delhivery","DELHIVERY"),
        ("IRCTC","IRCTC"),("RITES","RITES"),("IRFC","IRFC"),("Rail Vikas Nigam","RVNL"),
        ("Adani Wilmar","AWL"),("Interglobe Aviation","INDIGO"),("TCI Express","TCIEXP"),
        ("Gati","GATI"),("VRL Logistics","VRLLOG"),("Allcargo Logistics","ALLCARGO"),
        ("Transport Corp","TCI"),("Navkar Corp","NAVKARCORP"),
    ],
    "🔬 Chemicals & Fertilizers": [
        ("UPL","UPL"),("PI Industries","PIIND"),("Coromandel Int.","COROMANDEL"),
        ("Bayer CropScience","BAYERCROP"),("Sumitomo Chemical","SUMICHEM"),("Rallis India","RALLIS"),
        ("Deepak Nitrite","DEEPAKNTR"),("Aarti Industries","AARTIIND"),("Navin Fluorine","NAVINFLUOR"),
        ("SRF Limited","SRF"),("Vinati Organics","VINATIORGA"),("Galaxy Surfactants","GALAXYSURF"),
        ("Fine Organics","FINEORG"),("Balaji Amines","BALAMINES"),("Alkyl Amines","ALKYLAMINE"),
        ("Neogen Chemicals","NEOGEN"),("Clean Science","CLEAN"),("Anupam Rasayan","ANURAS"),
        ("Tata Chemicals","TATACHEM"),("GHCL","GHCL"),("Gujarat Fluorochemicals","FLUOROCHEM"),
        ("Himadri Speciality","HSCL"),("Sudarshan Chemical","SUDARSCHEM"),("NOCIL","NOCIL"),
        ("Chambal Fertilisers","CHAMBLFERT"),("NFL","NFL"),("GSFC","GSFC"),("RCF","RCF"),("FACT","FACT"),
        ("Atul Ltd","ATUL"),("Rossari Biotech","ROSSARI"),("Tatva Chintan","TATVA"),
        ("Ami Organics","AMIORG"),("Archean Chemical","ARCHEAN"),
    ],
    "🏠 Real Estate": [
        ("Godrej Properties","GODREJPROP"),("DLF","DLF"),("Prestige Estates","PRESTIGE"),
        ("Brigade Enterprises","BRIGADE"),("Sobha","SOBHA"),("Oberoi Realty","OBEROIRLTY"),
        ("Macrotech (Lodha)","LODHA"),("Mahindra Lifespace","MAHLIFE"),("Kolte Patil","KOLTEPATIL"),
        ("Puravankara","PURVA"),("DB Realty","DBREALTY"),("Indiabulls Real Estate","IBREALEST"),
        ("Embassy REIT","EMBASSY"),("Mindspace REIT","MINDSPACE"),("Brookfield REIT","BIRET"),
        ("Nexus Select Trust","NEXUSSELCT"),("Sunteck Realty","SUNTECK"),("Phoenix Mills","PHOENIXLTD"),
        ("Shriram Properties","SHRIRAMPPS"),("Signature Global","SIGNATURE"),
    ],
    "📡 Telecom & Media": [
        ("Bharti Airtel","BHARTIARTL"),("Vodafone Idea","IDEA"),("MTNL","MTNL"),
        ("Tata Communications","TATACOMM"),("Route Mobile","ROUTE"),("Tanla Platforms","TANLA"),
        ("Dish TV","DISHTV"),("Zee Entertainment","ZEEL"),("Sun TV Network","SUNTV"),
        ("PVR Inox","PVRINOX"),("Saregama India","SAREGAMA"),("Nazara Technologies","NAZARA"),
        ("Network18 Media","NETWORK18"),("TV18 Broadcast","TV18BRDCST"),
        ("Hathway Cable","HATHWAY"),("Den Networks","DEN"),("Indiacast Media","INDIACAST"),
    ],
    "🧵 Textiles & Apparel": [
        ("Page Industries","PAGEIND"),("Lux Industries","LUXIND"),("Dollar Industries","DOLLAR"),
        ("Trident","TRIDENT"),("Welspun India","WELSPUNIND"),("Raymond","RAYMOND"),
        ("Arvind","ARVIND"),("Vardhman Textiles","VTL"),("KPR Mill","KPRMILL"),
        ("Siyaram Silk Mills","SIYARAM"),("Nitin Spinners","NITINSPIN"),
        ("Indo Count Industries","ICIL"),("Gokaldas Exports","GOKEX"),("TCNS Clothing","TCNSBRANDS"),
        ("Go Fashion","GOCOLORS"),("Monte Carlo","MONTECARLO"),("Kewal Kiran","KKCL"),
    ],
    "🔌 Electronics & Capital Equipment": [
        ("Dixon Technologies","DIXON"),("Amber Enterprises","AMBER"),("Voltas","VOLTAS"),
        ("Blue Star","BLUESTARCO"),("Havells India","HAVELLS"),("Polycab India","POLYCAB"),
        ("KEI Industries","KEI"),("Finolex Cables","FINCABLES"),("V-Guard","VGUARD"),
        ("Crompton Greaves","CROMPTON"),("Orient Electric","ORIENTELEC"),("Bajaj Electricals","BAJAJELEC"),
        ("Whirlpool India","WHIRLPOOL"),("Kaynes Technology","KAYNES"),("Syrma SGS","SYRMA"),
        ("Elin Electronics","ELIN"),("Avalon Technologies","AVALON"),
        ("CDSL","CDSL"),("BSE Ltd","BSE"),("MCX India","MCX"),("Multi Comm Exchange","MCX"),
        ("Genus Power","GENUSPOWER"),("Apar Industries","APARINDS"),("Transformers & Rectifiers","TRIL"),
    ],
    "🌾 Agriculture & Food": [
        ("ITC (Agri)","ITC"),("Kaveri Seed","KSCL"),("Dhanuka Agritech","DHANUKA"),
        ("Venky's India","VENKEYS"),("Avanti Feeds","AVANTIFEED"),("Waterbase","WATERBASE"),
        ("Heritage Foods","HERITGFOOD"),("CCL Products","CCL"),("Agro Tech Foods","AGROTECH"),
        ("Adani Wilmar","AWL"),("Patanjali Foods","PATANJALI"),("Krbl","KRBL"),
        ("LT Foods","LTFOODS"),("Triveni Engineering","TRIVENI"),("Balrampur Chini","BALRAMCHIN"),
        ("Dalmia Bharat Sugar","DALMIASUG"),("EID Parry","EIDPARRY"),("Bajaj Hindusthan","BAJAJHIND"),
        ("Shakti Pumps","SHAKTIPUMP"),("Jain Irrigation","JISLJALEQS"),
    ],
    "🏛️ PSU & Defence": [
        ("HAL","HAL"),("BEL","BEL"),("BEML","BEML"),("Mazagon Dock","MAZDOCK"),
        ("Garden Reach Shipbuilders","GRSE"),("Cochin Shipyard","COCHINSHIP"),("MTNL","MTNL"),
        ("Bharat Dynamics","BDL"),("Data Patterns","DATAPATTNS"),("Paras Defence","PARAS"),
        ("Solar Industries","SOLARINDS"),("Munitions India","MIL"),("GRSE","GRSE"),
        ("RVNL","RVNL"),("IRFC","IRFC"),("IREDA","IREDA"),("NHPC","NHPC"),
        ("SJVN","SJVN"),("NTPC","NTPC"),("PGCIL","POWERGRID"),("NMDC","NMDC"),
        ("SAIL","SAIL"),("Coal India","COALINDIA"),("ONGC","ONGC"),("IOC","IOC"),
        ("BPCL","BPCL"),("HPCL","HPCL"),("GAIL India","GAIL"),
    ],
}

ALL_STOCKS = {}
for sector, stocks in SECTORS.items():
    for name, sym in stocks:
        key = f"{name} ({sym})"
        if key not in ALL_STOCKS:
            ALL_STOCKS[key] = f"{sym}.NS"


def resolve_search_input(search_text: str):
    """
    Resolves search string to (ticker, display_name, is_dashboard).
    """
    search = search_text.strip()
    if not search:
        return "^NSEI", "NIFTY 50", True

    sl = search.lower()
    match_t, match_n = None, None
    for label, ticker in ALL_STOCKS.items():
        if sl in label.lower():
            match_t, match_n = ticker, label.split(" (")[0]
            break

    if not match_t:
        for label, ticker in ALL_STOCKS.items():
            sym = ticker.replace(".NS", "")
            if sl.upper() == sym or sl.upper() == ticker.upper():
                match_t, match_n = ticker, label.split(" (")[0]
                break

    if match_t:
        return match_t, match_n, False

    candidate = search.upper()
    if not candidate.endswith(".NS") and not candidate.endswith(".BO") and "^" not in candidate:
        candidate = candidate + ".NS"
    return candidate, search.upper().replace(".NS", "").replace(".BO", ""), False


def render_search_bar():
    """
    Renders global stock search component.
    """
    if "search_val" not in st.session_state:
        st.session_state["search_val"] = ""

    def _clear_search_value():
        st.session_state["search_val"] = ""

    st.markdown("<div style='background:rgba(7,18,32,0.45);border:1px solid rgba(0,200,255,0.12);padding:10px 16px;border-radius:6px;margin-bottom:12px;'>", unsafe_allow_html=True)
    sc1, sc2 = st.columns([5, 1])
    with sc1:
        search_raw = st.text_input("Search", placeholder="Search any NSE/BSE stock - name or symbol (e.g. Reliance, TCS, SBIN, INFY)...", label_visibility="collapsed", key="search_val")
    with sc2:
        if search_raw:
            st.button("Clear", use_container_width=True, on_click=_clear_search_value)
    st.markdown("</div>", unsafe_allow_html=True)

    return resolve_search_input(search_raw)
