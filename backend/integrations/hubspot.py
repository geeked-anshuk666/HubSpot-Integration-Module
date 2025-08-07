import json
import secrets
import asyncio
import httpx
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from .integration_item import IntegrationItem # Corrected import path

# HubSpot OAuth configuration
CLIENT_ID = "325426ca-6738-488a-acdc-fefeb0d73daf"  # Replace with your HubSpot client ID
CLIENT_SECRET = "d03c5f26-7961-4312-9901-152e1e8089d1"  # Replace with your HubSpot client secret
REDIRECT_URI = "http://localhost:8000/integrations/hubspot/oauth2callback"
AUTHORIZATION_URL = f"https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=oauth%20crm.objects.contacts.read"

# Base64 encoded client_id:client_secret for Authorization header
# This line is not needed as client_id and client_secret are sent in form data for token exchange.
# encoded_client_id_secret = httpx.BasicAuth(CLIENT_ID, CLIENT_SECRET).encode().decode()

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{AUTHORIZATION_URL}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubspot.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'code': code,
                    'redirect_uri': REDIRECT_URI
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

def create_integration_item_metadata_object(item, item_type):
    """Create an IntegrationItem object from HubSpot data"""
    integration_item = IntegrationItem(
        id=item.get('id', ''),
        name=item.get('properties', {}).get('name', '') or item.get('properties', {}).get('firstname', '') + ' ' + item.get('properties', {}).get('lastname', ''),
        type=item_type,
        url=f"https://app.hubspot.com/{item_type}/{item.get('id', '')}",
        description=item.get('properties', {}).get('description', '') or item.get('properties', {}).get('notes', ''),
        created_at=item.get('createdAt', ''),
        updated_at=item.get('updatedAt', ''),
        owner=item.get('properties', {}).get('hubspot_owner_id', ''),
        status=item.get('properties', {}).get('hs_lead_status', '') or item.get('properties', {}).get('dealstage', ''),
    )
    return integration_item

async def get_items_hubspot(credentials) -> list[IntegrationItem]:
    """Aggregates all metadata relevant for a hubspot integration"""
    credentials = json.loads(credentials)
    access_token = credentials.get("access_token")
    
    # Lists to store different types of HubSpot items
    contacts = []
    companies = []
    deals = []
    
    # Fetch contacts
    contacts_response = httpx.get(
        'https://api.hubapi.com/crm/v3/objects/contacts',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        params={
            'limit': 100,
            'properties': 'firstname,lastname,email,phone,notes,hs_lead_status,createdate,lastmodifieddate'
        }
    )
    
    if contacts_response.status_code == 200:
        contacts_data = contacts_response.json()
        for contact in contacts_data.get('results', []):
            contacts.append(create_integration_item_metadata_object(contact, 'contacts'))
    
    # Fetch companies
    companies_response = httpx.get(
        'https://api.hubapi.com/crm/v3/objects/companies',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        params={
            'limit': 100,
            'properties': 'name,domain,description,industry,website,createdate,hs_lastmodifieddate'
        }
    )
    
    if companies_response.status_code == 200:
        companies_data = companies_response.json()
        for company in companies_data.get('results', []):
            companies.append(create_integration_item_metadata_object(company, 'companies'))
    
    # Fetch deals
    deals_response = httpx.get(
        'https://api.hubapi.com/crm/v3/objects/deals',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        params={
            'limit': 100,
            'properties': 'dealname,amount,dealstage,description,createdate,hs_lastmodifieddate'
        }
    )
    
    if deals_response.status_code == 200:
        deals_data = deals_response.json()
        for deal in deals_data.get('results', []):
            deals.append(create_integration_item_metadata_object(deal, 'deals'))
    
    # Combine all items
    all_items = contacts + companies + deals
    
    # Convert IntegrationItem objects to dictionaries, excluding None values
    # This will remove fields like parent_path_or_name, children, etc., if they are None
    clean_items = [item.dict(exclude_none=True) for item in all_items]
    
    print(clean_items) # Print the cleaned items for debugging
    return clean_items