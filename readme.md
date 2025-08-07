# HubSpot Integration Module (`hubspot.py`)

This module handles the integration with HubSpot, including OAuth 2.0 authorization, credential management, and fetching CRM data (contacts, companies, and deals). It leverages FastAPI for API endpoints, `httpx` for asynchronous HTTP requests, and Redis for temporary storage of OAuth states and credentials.

## Configuration

The module requires the following HubSpot OAuth application details:

*   **`CLIENT_ID`**: Your HubSpot application's client ID.
*   **`CLIENT_SECRET`**: Your HubSpot application's client secret.
*   **`REDIRECT_URI`**: The URI where HubSpot redirects after authorization, which must be registered in your HubSpot app settings.

## Key Functions

### `authorize_hubspot(user_id, org_id)`

*   **Purpose**: Initiates the HubSpot OAuth 2.0 authorization flow.
*   **Details**:
    *   Generates a unique `state` parameter (using `secrets.token_urlsafe`) to prevent Cross-Site Request Forgery (CSRF) attacks.
    *   Combines the `state`, `user_id`, and `org_id` into an encoded JSON string.
    *   Stores this encoded state in Redis with a 10-minute expiration, keyed by `hubspot_state:{org_id}:{user_id}`.
    *   Constructs and returns the full HubSpot authorization URL, including the client ID, redirect URI, required scopes (`oauth crm.objects.contacts.read`), and the encoded state.

### `oauth2callback_hubspot(request: Request)`

*   **Purpose**: Handles the callback from HubSpot after a user authorizes the application.
*   **Details**:
    *   Checks for any authorization errors returned by HubSpot.
    *   Extracts the `code` (authorization code) and `encoded_state` from the request query parameters.
    *   Decodes the `encoded_state` to retrieve the original `state`, `user_id`, and `org_id`.
    *   Retrieves the `saved_state` from Redis using the `org_id` and `user_id`.
    *   Validates that the `original_state` matches the `saved_state` to ensure security.
    *   Performs an asynchronous POST request to HubSpot's token endpoint (`https://api.hubspot.com/oauth/v1/token`) to exchange the authorization `code` for an access token and refresh token.
    *   Concurrently, deletes the temporary `hubspot_state` from Redis.
    *   Stores the obtained HubSpot credentials (access token, refresh token, etc.) in Redis, keyed by `hubspot_credentials:{org_id}:{user_id}`, with a 10-minute expiration.
    *   Returns an `HTMLResponse` with a JavaScript snippet to close the pop-up window on the client side.

### `get_hubspot_credentials(user_id, org_id)`

*   **Purpose**: Retrieves the stored HubSpot credentials for a specific user and organization.
*   **Details**:
    *   Fetches the credentials from Redis using the `org_id` and `user_id`.
    *   Raises an `HTTPException` if no credentials are found.
    *   Parses the JSON string credentials into a Python dictionary.
    *   Deletes the credentials from Redis after retrieval (as they are temporary for the current session).
    *   Returns the credentials dictionary.

### `create_integration_item_metadata_object(item, item_type)`

*   **Purpose**: Transforms raw HubSpot API response data into a standardized `IntegrationItem` object.
*   **Details**:
    *   Takes a HubSpot item dictionary and its `item_type` (e.g., 'contacts', 'companies', 'deals') as input.
    *   Maps relevant HubSpot properties (e.g., `id`, `name`, `firstname`, `lastname`, `description`, `notes`, `createdAt`, `updatedAt`, `hubspot_owner_id`, `hs_lead_status`, `dealstage`) to the fields of the `IntegrationItem` Pydantic model.
    *   Constructs a HubSpot-specific URL for the item.
    *   Returns an instance of `IntegrationItem`.

### `get_items_hubspot(credentials) -> list[IntegrationItem]`

*   **Purpose**: Aggregates and returns a list of `IntegrationItem` objects from various HubSpot CRM endpoints.
*   **Details**:
    *   Takes the HubSpot credentials (containing the `access_token`) as input.
    *   Makes separate asynchronous GET requests to HubSpot's CRM API for:
        *   Contacts (`/crm/v3/objects/contacts`)
        *   Companies (`/crm/v3/objects/companies`)
        *   Deals (`/crm/v3/objects/deals`)
    *   For each type, it requests specific properties relevant to the `IntegrationItem` model.
    *   Iterates through the results of each API call and uses `create_integration_item_metadata_object` to convert them into `IntegrationItem` instances.
    *   Combines all fetched contacts, companies, and deals into a single list.
    *   **Crucially**, it converts each `IntegrationItem` object into a dictionary using `item.dict(exclude_none=True)`. This ensures that any fields in the `IntegrationItem` model that are `None` (because they are not applicable to HubSpot items, e.g., `parent_path_or_name`, `children`) are excluded from the final JSON output, resulting in cleaner and more concise data.
    *   Prints the cleaned list of items to the console for debugging purposes.
    *   Returns the list of cleaned item dictionaries.

## Dependencies

*   `json`: For JSON encoding and decoding.
*   `secrets`: For generating secure random strings (for OAuth state).
*   `asyncio`: For asynchronous operations.
*   `httpx`: An asynchronous HTTP client for making API requests to HubSpot.
*   `fastapi`: Used for defining API routes and handling HTTP requests/responses.
*   `fastapi.responses.HTMLResponse`: For returning HTML content.
*   `redis_client`: A custom module for interacting with Redis (adding, getting, and deleting key-value pairs).
*   `integration_item.IntegrationItem`: A Pydantic `BaseModel` defining the standardized structure for integration items across different platforms.