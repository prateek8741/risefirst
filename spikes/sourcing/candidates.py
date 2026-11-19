"""Candidate company slugs for the sourcing spike.

These are *guesses* at ATS board slugs (usually the lower-cased company name).
A slug that resolves is not proof it is the company we think: generic words
(e.g. "open", "loop", "plum") may belong to an unrelated employer. Boards with
India jobs are listed in the report for manual verification before any of them
go into config/sources.yaml.
"""

INDIAN_STARTUPS = """
razorpay razorpaysoftwareprivatelimited zerodha groww cred meesho swiggy zomato zepto
blinkit phonepe paytm flipkart myntra nykaa olacabs olaelectric krutrim oyo oyorooms
byjus unacademy upgrad physicswallah vedantu eruditus simplilearn scaler interviewbit
freshworks zoho chargebee postman browserstack druva icertis innovaccer highradius
mindtickle whatfix leadsquared moengage clevertap webengage netcore capillarytech
darwinbox keka zeta zetasuite juspay cashfree pinelabs jupitermoney epifi sliceit
onecard navi acko godigit policybazaar pbfintech insurancedekho cars24 spinny cardekho
girnarsoft urbancompany dunzo bigbasket licious freshtohome countrydelight rebelfoods
curefit practo pharmeasy tata1mg medibuddy healthifyme qureai sharechat mohalla
dailyhunt inmobi glance rapido porter delhivery shiprocket blackbuck loadshare
xpressbees udaan jumbotail dealshare citymall khatabook okcredit vyapar bharatpe
instamojo setu m2p perfios signzy idfy hyperverge lentra kredx lendingkart indifi
smallcase upstox angelone dhan indmoney sprinklr hasura atlan rocketlane zluri
spotdraft gupshup yellowai haptik uniphore observeai exotel kapture zenoti kissflow
facilio plum onsurity eloelo sarvam sarvamai pocketfm kukufm seekho classplus
teachmint leapfinance yocket cuemath doubtnut adda247 testbook embibe nobroker
housing squareyards livspace homelane furlenco rentomojo lenskart boat mamaearth
honasa purplle firstcry bluestone caratlane pepperfry ixigo makemytrip cleartrip
easemytrip redbus zoomcar yulu atherenergy simpleenergy eulermotors batterysmart
ultraviolette agnikul skyroot pixxel ideaforge appsmith tooljet hoppscotch signoz
devrev lambdatest testsigma wingify hevodata sigmoid tredence fractal fractalanalytics
musigma latentview tigeranalytics quantiphi gramener affine mathco themathcompany
course5 shipsy mintoak locus fareye increff unicommerce zetwerk ofbusiness infra-market
moglix jar fampay junio stashfin kissht kreditbee moneyview fibe earlysalary truecaller
bobble koo nearbuy magicpin thrillophilia airmeet hubilo zinghr springworks
""".split()

ANALYTICS_AND_SERVICES = """
zsassociates axtria evalueserve eclerx exlservice wns genpact crisil thoughtworks
publicissapient nagarro globant epam griddynamics endava persistent tigeranalyticsinc
mphasis hexaware coforge zensar sonata cyient ltts kpit tataelxsi happiestminds
infobeans cybage synechron virtusa birlasoft mastek 3i-infotech
""".split()

GLOBAL_WITH_INDIA_OFFICES = """
databricks stripe mongodb okta rubrik twilio coinbase cloudflare elastic gitlab
hashicorp confluent datadog dropbox airbnb pinterest reddit discord robinhood plaid
brex gusto figma asana airtable zendesk intercom wise agoda booking expedia toptal
turing deel remotecom rippling harnessinc sumologic newrelic nutanix purestorage
couchbase cohesity commvault zscaler crowdstrike sentinelone tanium snowflake fivetran
dbtlabs starburst clickhouse singlestore yugabyte cockroachlabs redis neo4j grafanalabs
vercel netlify supabase anthropic openai scaleai cohere perplexity glean notion canva
miro atlassian gojek grab careem nium airwallex rapyd checkout adyen klarna revolut
chime affirm marqeta toast block doordash instacart lyft uber samsara servicetitan
duolingo coursera udemy chegg thoughtspot mixpanel amplitude segment postscript
braze contentsquare sprinklrinc freshdesk hubspot zoominfo gong outreach clari
highspot seismic sisense tableau alteryx dataiku collibra informatica talend
workato celonis uipath automationanywhere blueprism appian pega outsystems mendix
servicenow salesforce adobe intuit paypal visa mastercard americanexpress
goldmansachs morganstanley jpmorgan barclays deutschebank citi hsbc
wellsfargo ubs nomura blackrock statestreet fidelity vanguard
""".split()

ALL_CANDIDATES: list[str] = sorted(set(INDIAN_STARTUPS + ANALYTICS_AND_SERVICES + GLOBAL_WITH_INDIA_OFFICES))
