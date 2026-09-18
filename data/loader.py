import time
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import pandas as pd
import yfinance as yf
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# COMPLETE NSE/BSE STOCK UNIVERSE — 600+ STOCKS
# ══════════════════════════════════════════════════════════════════════════════
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
        ("Nippon India AMC","NAMINDIA"),("UTI AMC","UTIAMC"),("Aditya Birla AMC","ABSLAMC"),
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
        ("Hexaware","TECHM"),("Birlasoft","BSOFT"),("Intellect Design","INTELLECT"),
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
        ("Texmaco Rail","TEXRAIL"),("Jupiter Wagons","JWL"),("Titagarh Rail","TITAGARH"),
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
        ("Jaiprakash Power","JPPOWER"),("Mangalore Refinery","MRPL"),
        ("Chennai Petroleum","CHENNPETRO"),("GIPCL","GIPCL"),("TNPL","TNPL"),
        ("Premier Energies","PREMIERENE"),
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
        ("Jindal Stainless","JSL"),("Jindal Steel & Power","JINDALSTEL"),("Steel Authority","SAIL"),
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
        ("Westlife Foodworld","WESTLIFE"),
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
        ("Adani Ports","ADANIPORTS"),("GMR Airports","GMRAIRPORT"),("IndiGo","INDIGO"),
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

# Legacy / delisted symbols -> current Yahoo Finance tickers
SYMBOL_ALIASES = {
    "TEXRAILWAG": "TEXRAIL",
    "HEXAWARE": "TECHM",
    "BURGERKING": "WESTLIFE",
    "JINDALPOLY": "JINDALSTEL",
    "JSPL": "JINDALSTEL",
    "CPCL": "MRPL",
    "GKLENERGY": "NTPC",
    "ACMESOLAR": "PREMIERENE",
    "GMRINFRA": "GMRAIRPORT",
    "NAM-INDIA": "NAMINDIA",
    "TATAMOTORS": "TMCV",
}

US_STOCKS_SET = {
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "INTC",
    "QCOM", "PLTR", "SPY", "QQQ", "BTC-USD", "ETH-USD", "COIN", "NFLX", "DIS", "BA",
    "^GSPC", "^IXIC", "^DJI"
}

def resolve_ticker(ticker_input: str, market_mode: str = "Indian Market") -> str:
    ticker_input = ticker_input.strip().upper()
    if ticker_input.endswith(".NS") or ticker_input.endswith(".BO") or "^" in ticker_input or "-" in ticker_input:
        base = ticker_input.replace(".NS", "").replace(".BO", "")
        if base in SYMBOL_ALIASES:
            suffix = ".NS" if ticker_input.endswith(".NS") else (".BO" if ticker_input.endswith(".BO") else ".NS")
            return f"{SYMBOL_ALIASES[base]}{suffix}"
        return ticker_input
    if ticker_input in US_STOCKS_SET or "US" in market_mode:
        return ticker_input
    if ticker_input in SYMBOL_ALIASES:
        return f"{SYMBOL_ALIASES[ticker_input]}.NS"
    for key, val in ALL_STOCKS.items():
        sym = val.replace(".NS","").replace(".BO","").upper()
        if ticker_input == sym:
            return val
    return f"{ticker_input}.NS"

def get_sector_peers(ticker_symbol: str, max_peers: int = 2) -> tuple[str | None, list[str]]:
    clean = ticker_symbol.replace(".NS","").replace(".BO","").upper()
    for sector, list_of_stocks in SECTORS.items():
        if any(sym == clean for _, sym in list_of_stocks):
            peers = []
            for name, sym in list_of_stocks:
                if sym != clean:
                    peers.append(f"{sym}.NS")
                    if len(peers) >= max_peers:
                        break
            return sector, peers
    return None, []

@st.cache_data(ttl=3600, show_spinner=False)
def load_ohlcv(ticker: str, period: str = "5y") -> pd.DataFrame | None:
    def _fetch(sym: str):
        try:
            df = yf.download(sym, period=period, interval="1d", auto_adjust=True,
                              progress=False, timeout=12)
            if df is None or df.empty:
                return None
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.reset_index()
            df.columns = [str(c).strip() for c in df.columns]
            for col in ["Open","High","Low","Close","Volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["Close"])
            return df if len(df) >= 20 else None
        except Exception:
            return None

    df = _fetch(ticker)
    if df is not None:
        return df
    base = ticker.replace(".NS", "").replace(".BO", "").upper()
    alias = SYMBOL_ALIASES.get(base)
    if alias:
        suffix = ".NS" if ".BO" not in ticker else ".BO"
        return _fetch(f"{alias}{suffix}")
    if ticker.endswith(".NS"):
        return _fetch(ticker.replace(".NS", ".BO"))
    return None

def _download_raw(ticker: str, period: str = "1y") -> pd.DataFrame | None:
    try:
        df = yf.download(ticker, period=period, interval="1d", auto_adjust=True,
                          progress=False, timeout=8, threads=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        df.columns = [str(c).strip() for c in df.columns]
        for col in ["Open","High","Low","Close","Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["Close"])
        return df
    except Exception:
        return None

@st.cache_data(ttl=1800, show_spinner=False)
def load_indices(market_mode: str = "Indian Market") -> dict[str, pd.DataFrame]:
    if "US" in market_mode:
        tickers = ["^GSPC","^IXIC","^DJI","^RUT","BTC-USD","^VIX"]
    else:
        tickers = ["^NSEI","^NSEBANK","^BSESN","^CRSMID","^CNXSC","^INDIAVIX"]
    results = {}
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", auto_adjust=True, progress=False)
            if d is not None and not d.empty:
                if isinstance(d.columns, pd.MultiIndex):
                    d.columns = d.columns.get_level_values(0)
                d = d.reset_index()
                results[t] = d
        except Exception:
            pass
    return results

@st.cache_data(ttl=900, show_spinner=False)
def fetch_news(ticker: str, company_name: str = "") -> list[dict]:
    clean = ticker.replace(".NS", "").replace(".BO", "")
    query = company_name.strip() if company_name.strip() else clean
    items = []
    try:
        gquery = urllib.parse.quote(f"{query} stock NSE")
        gurl = f"https://news.google.com/rss/search?q={gquery}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(gurl, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            root = ET.fromstring(r.read())
        for item in root.findall(".//item")[:15]:
            title   = (item.find("title").text   or "") if item.find("title")   is not None else ""
            link    = (item.find("link").text    or "") if item.find("link")    is not None else ""
            pubdate = (item.find("pubDate").text or "") if item.find("pubDate") is not None else ""
            if title:
                items.append({"title": title, "link": link, "date": pubdate[:16]})
    except Exception:
        pass

    if items:
        return items

    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={clean}&region=IN&lang=en-IN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            root = ET.fromstring(r.read())
        for item in root.findall(".//item"):
            title   = (item.find("title").text   or "") if item.find("title")   is not None else ""
            link    = (item.find("link").text    or "") if item.find("link")    is not None else ""
            pubdate = (item.find("pubDate").text or "") if item.find("pubDate") is not None else ""
            items.append({"title": title, "link": link, "date": pubdate[:16]})
        return items
    except Exception:
        return []

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fii_dii():
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/fii-dii-activity",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        main_req = urllib.request.Request("https://www.nseindia.com", headers=headers)
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        opener.open(main_req, timeout=8)
        time.sleep(0.5)
        with opener.open(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        return data
    except Exception:
        return None

def parse_fii_dii(data):
    if not data:
        return None, None
    try:
        rows = data if isinstance(data, list) else data.get("data", [])
        records = []
        for row in rows[:20]:
            try:
                date_str = row.get("date", row.get("Date", ""))
                fii_buy  = float(str(row.get("fiiBuy",  row.get("FII_BUY",  0))).replace(",","") or 0)
                fii_sell = float(str(row.get("fiiSell", row.get("FII_SELL", 0))).replace(",","") or 0)
                dii_buy  = float(str(row.get("diiBuy",  row.get("DII_BUY",  0))).replace(",","") or 0)
                dii_sell = float(str(row.get("diiSell", row.get("DII_SELL", 0))).replace(",","") or 0)
                records.append({
                    "Date": date_str,
                    "FII Net": round(fii_buy - fii_sell, 2),
                    "DII Net": round(dii_buy - dii_sell, 2),
                    "FII Buy": fii_buy, "FII Sell": fii_sell,
                    "DII Buy": dii_buy, "DII Sell": dii_sell,
                })
            except Exception:
                continue
        if not records:
            return None, None
        df = pd.DataFrame(records)
        return df, df.iloc[0] if len(df) > 0 else None
    except Exception:
        return None, None

@st.cache_data(ttl=900, show_spinner=False)
def fetch_options_chain(symbol: str):
    clean = symbol.replace(".NS","").replace(".BO","").upper()
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={clean}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.nseindia.com/get-quotes/derivatives?symbol={clean}",
    }
    try:
        import http.cookiejar
        cj   = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        main_req = urllib.request.Request("https://www.nseindia.com", headers=headers)
        opener.open(main_req, timeout=8)
        time.sleep(0.5)
        req = urllib.request.Request(url, headers=headers)
        with opener.open(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def parse_options_chain(data, spot_price: float):
    if not data:
        return None, None, None, None
    try:
        records = data.get("records", {})
        exp_dates = records.get("expiryDates", [])
        nearest_exp = exp_dates[0] if exp_dates else None
        chain_data  = records.get("data", [])

        rows = []
        for item in chain_data:
            if nearest_exp and item.get("expiryDate") != nearest_exp:
                continue
            strike = item.get("strikePrice", 0)
            ce = item.get("CE", {})
            pe = item.get("PE", {})
            rows.append({
                "Strike":   strike,
                "CE OI":    ce.get("openInterest", 0),
                "CE Chg OI": ce.get("changeinOpenInterest", 0),
                "CE LTP":   ce.get("lastPrice", 0),
                "CE IV":    ce.get("impliedVolatility", 0),
                "PE OI":    pe.get("openInterest", 0),
                "PE Chg OI": pe.get("changeinOpenInterest", 0),
                "PE LTP":   pe.get("lastPrice", 0),
                "PE IV":    pe.get("impliedVolatility", 0),
            })

        if not rows:
            return None, None, None, nearest_exp

        df_chain = pd.DataFrame(rows).sort_values("Strike")

        total_ce_oi = df_chain["CE OI"].sum()
        total_pe_oi = df_chain["PE OI"].sum()
        pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else None

        strikes = df_chain["Strike"].values
        ce_ois  = df_chain["CE OI"].values
        pe_ois  = df_chain["PE OI"].values
        pain    = []
        for s in strikes:
            ce_pain = sum(max(0, s - k) * o for k, o in zip(strikes, ce_ois))
            pe_pain = sum(max(0, k - s) * o for k, o in zip(strikes, pe_ois))
            pain.append(ce_pain + pe_pain)
        max_pain_strike = float(strikes[int(np.argmin(pain))])

        return df_chain, pcr, max_pain_strike, nearest_exp
    except Exception as e:
        return None, None, None, None

def _parse_ratio_li(html: str, label: str):
    li_pattern = re.compile(
        r'<li[^>]*>\s*<span class="name">\s*(?:<a[^>]*>)?\s*' + re.escape(label) +
        r'\s*(?:</a>)?\s*</span>(.*?)</li>', re.IGNORECASE | re.DOTALL
    )
    m = li_pattern.search(html)
    if not m:
        return None
    block = m.group(1)
    nums = re.findall(r'-?[\d]+(?:,\d{3})*(?:\.\d+)?', block)
    if not nums:
        return None
    try:
        return float(nums[-1].replace(",", ""))
    except Exception:
        return None

def _sane(value, lo, hi):
    if value is None:
        return None
    return value if lo <= value <= hi else None

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fundamentals(symbol: str) -> tuple[dict, str]:
    clean = symbol.replace(".NS", "").replace(".BO", "").upper()
    url   = f"https://www.screener.in/company/{clean}/consolidated/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception:
        try:
            url2 = f"https://www.screener.in/company/{clean}/"
            req2 = urllib.request.Request(url2, headers=headers)
            with urllib.request.urlopen(req2, timeout=10) as r:
                html = r.read().decode("utf-8", errors="ignore")
            url = url2
        except Exception:
            return {}, url

    pe   = _sane(_parse_ratio_li(html, "Stock P/E"),         0, 500)
    pb   = _sane(_parse_ratio_li(html, "Price to Book value"), 0, 100)
    roe  = _sane(_parse_ratio_li(html, "ROE"),                -100, 100)
    roce = _sane(_parse_ratio_li(html, "ROCE"),               -100, 100)
    de   = _sane(_parse_ratio_li(html, "Debt to equity"),      0, 20)
    prom = _sane(_parse_ratio_li(html, "Promoter holding"),    0, 100)
    eps  = _sane(_parse_ratio_li(html, "EPS"),                -1000, 100000)
    dy   = _sane(_parse_ratio_li(html, "Dividend Yield"),       0, 25)

    return {
        "P/E Ratio":      pe,
        "P/B Ratio":      pb,
        "ROE (%)":        roe,
        "ROCE (%)":       roce,
        "Debt/Equity":    de,
        "Promoter Hold%": prom,
        "EPS (TTM)":      eps,
        "Div Yield (%)":  dy,
    }, url

@st.cache_data(ttl=300, show_spinner=False)
def load_intraday(ticker: str, interval: str = "5m", period: str = "5d") -> pd.DataFrame | None:
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False, timeout=10)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return None
