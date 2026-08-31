# Auth-Gated App Testing Playbook (Emergent Google Auth)

NOTE: In Nugvio, users collection uses `id` (not `user_id`). Sessions in `user_sessions` store `user_id` = users.id.

## Step 1: Create Test User & Session
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  nug_points: 100,
  streak_days: 1,
  created_at: new Date().toISOString()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
  created_at: new Date().toISOString()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"

## Step 2: Test Backend API
curl -X GET "$API_URL/api/auth/me" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
curl -X GET "$API_URL/api/expenses" -H "Authorization: Bearer YOUR_SESSION_TOKEN"

## Step 3: Browser Testing
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "your-app.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}])
await page.goto("https://your-app.com/app")

## Cleanup
mongosh --eval "
use('test_database');
db.users.deleteMany({email: /test\.user\./});
db.user_sessions.deleteMany({session_token: /test_session/});
"

## Success Indicators
- /api/auth/me returns user data
- Dashboard loads without redirect to /login
- CRUD works with session token

## Failure Indicators
- 401 Unauthorized, "User not found", redirect to login

## Notes
- Backend session exchange endpoint: POST /api/auth/google/session {session_id}
- Session token also accepted via Authorization: Bearer header (fallback after JWT decode fails)
- Existing JWT email/password auth continues to work (demo@nugvio.in / Nugvio@123)
- Callback detection uses useLocation().hash in AppRoutes (App.js); AuthCallback at /app/frontend/src/components/AuthCallback.jsx
