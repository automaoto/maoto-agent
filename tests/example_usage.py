from maoto-agent-module import *
import time

# Set environment variables for testing
os.environ["RESOLVER_API_URL"] = "http://localhost:4000"

# Initialize Marketplace
os.environ["M_API_KEY"] = "test_admin_api_key"
time_start = time.time()
marketplace = Marketplace()
print("Time passed:", round(time.time() - time_start, 2))
userId = marketplace.get_userId()
print(f"Marketplace initialized with userId {userId}\n")

################## Management ##################

# TODO: auto API key generation
# TODO: auto admi first user creation

#Create test users and store hash from password in database
test_user1 = MNewUser("testusername1", "testpassword1")
test_user2 = MNewUser("testusername2", "testpassword2")
new_users = marketplace.create_users([test_user1, test_user2])
print("Time passed:", round(time.time() - time_start, 2))
print(f"Created users: {new_users}\n")

#Delete a user
delete_users_success = marketplace.delete_users(new_users[0])
print("Time passed:", round(time.time() - time_start, 2))
print(f"Delete user success: {delete_users_success}\n")

#Get all users
all_users = marketplace.get_users()
print("Time passed:", round(time.time() - time_start, 2))
print(f"All users: {all_users}\n")

# Create new api keys and store hash from api-key in database
test_api_key1 = MNewApiKey("test_api_key1", new_users[1]) # also works with user_id
test_api_key2 = MNewApiKey("test_api_key2", new_users[1]) # also works with user_id
api_keys, api_key_objects = marketplace.create_api_keys([test_user2])
print("Time passed:", round(time.time() - time_start, 2))
print(f"Api key ids: {api_key_objects}\n")

# Delete api key
delete_api_keys_success = marketplace.delete_api_keys([api_keys[0]])
print("Time passed:", round(time.time() - time_start, 2))
print(f"Delete api keys success: {delete_api_keys_success}\n")

# Get user api keys
api_keys = marketplace.get_api_keys([new_users[1]])
print("Time passed:", round(time.time() - time_start, 2))
print(f"Api keys: {api_keys}\n")
os.environ["M_API_KEY"] = api_keys[1]

################## For Task Provider ##################

# TODO: start status subscription to get task providers posts that resolved

# Create a post
m_task_parent = MTask("Hello, Kubernetes! parent", "Some context parent")
m_post = marketplace.post_tasks([m_task_parent])[0]
print("Time passed:", round(time.time() - time_start, 2))
print(f"Created post:\n{m_post}\n")

# Get the created post by ID
m_post_fetched = marketplace.get_posts([m_post.get_postId()])[0]
print("Time passed:", round(time.time() - time_start, 2))
print(f"Fetched post:\n{m_post_fetched}\n")

# Delete the parent post cascading children
delete_parent_success = marketplace.delete_posts([m_post])
print("Time passed:", round(time.time() - time_start, 2))
print(f"Delete parent post success: {delete_parent_success}\n")

################## For Resolver ##################

# TODO: Create connection to automatically be notified of new posts that are not resolved yet and close enough to bidder in the vectorspace

# TODO: create connection to automatically be notified of successful bids

# Bid on a post
bids = [MBid(m_post_fetched.get_postId(), 12.50)]
bid_success = marketplace.bid_on_posts(bids)
print("Time passed:", round(time.time() - time_start, 2))
print(f"Bid success: {bid_success}\n")

# Return bids on given posts
post_bids = marketplace.get_post_bids([m_post_fetched])
print("Time passed:", round(time.time() - time_start, 2))
print(f"Post bids: {post_bids}\n")

# Resolve the post
resolve_success = marketplace.resolve_posts([m_post]) # Note: This also accepts post ID: m_post.get_postId()
print("Time passed:", round(time.time() - time_start, 2))
print(f"Resolve success: {resolve_success}\n")

# Split a post
m_tasks_split = [MTask("Hello, Kubernetes!1", "Some context1"), MTask("Hello, Kubernetes!2", "Some context2")]
m_posts_split = marketplace.split_posts(m_post, m_tasks_split) # Note: This also accepts post ID: m_post.get_postId()
print("Time passed:", round(time.time() - time_start, 2))
print(f"Split posts: {m_posts_split}\n")

###### Management: Cleanup - Delete posts ######

# Get all posts
m_posts = marketplace.get_posts()
print("Time passed:", round(time.time() - time_start, 2))
print(f"All posts (Max 100): {m_posts}\n")

# delete all (everything should be deleted until here already anyways)
delete_parent_success = marketplace.delete_posts(m_posts)
print("Time passed:", round(time.time() - time_start, 2))
print(f"Deleted posts (should be empty array): {delete_parent_success}\n")
