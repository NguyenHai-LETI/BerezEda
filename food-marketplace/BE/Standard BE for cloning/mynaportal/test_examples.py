"""
Test example for the refactored MynaPortal endpoints.

This shows how to use the new endpoints with proper authentication.
"""

# Example of how the endpoints work:


def test_myna_authorizer_flow():
    """
    Example test showing the complete MynaPortal flow:
    1. Create authorizer and get authorization link
    2. User authorizes on MynaPortal
    3. Process the returned code to get welfare data
    """

    # Step 1: Create MynaAuthorizer and get authorization link
    # POST /mynaportal/myna_authorizer
    # Headers: Authorization: Bearer <token>
    # Body: {} (empty request)
    # Response: {"data": {"link_authorize": "https://..."}}

    # Step 2: User visits the authorization link and authorizes
    # MynaPortal redirects back with code and state parameters

    # Step 3: Process the authorization code
    # POST /mynaportal/process
    # Headers: Authorization: Bearer <token>
    # Body: {"code": "auth_code", "state": "12345678"}
    # Response: {"data": {"status": "success", "welfare_info": {...}}}


# Example curl commands:

# 1. Create authorizer (requires authentication)
"""
curl -X POST "http://localhost:8000/mynaportal/myna_authorizer" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d "{}"
"""

# 2. Process MyNumber data (requires authentication)
"""
curl -X POST "http://localhost:8000/mynaportal/process" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"code": "authorization_code", "state": "12345678"}'
"""

# 3. Callback from MynaPortal (no authentication required)
"""
curl -X POST "http://localhost:8000/mynaportal/users/myna_go_jp" \
  -H "Content-Type: application/json" \
  -d '{
    "commonHeader": {
      "telegramId": "TL-000086-240401000000-0000",
      "telegramType": "IFA0302-S01", 
      "mode": "1",
      "processId": "PROC123456",
      "errorCode": ""
    }
  }'
"""
