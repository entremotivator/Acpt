import streamlit as st
import requests
import json
import base64
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="WordPress CPT Manager",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'auth_header' not in st.session_state:
    st.session_state.auth_header = None
if 'wp_url' not in st.session_state:
    st.session_state.wp_url = ""
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"
if 'post_types' not in st.session_state:
    st.session_state.post_types = []
if 'current_posts' not in st.session_state:
    st.session_state.current_posts = []
if 'current_post_type' not in st.session_state:
    st.session_state.current_post_type = None
if 'current_post' not in st.session_state:
    st.session_state.current_post = None
if 'meta_boxes' not in st.session_state:
    st.session_state.meta_boxes = []

# Function to authenticate with WordPress using basic auth or application password
def authenticate(url, username, password):
    try:
        # Remove trailing slash if present
        url = url.rstrip('/')
        
        # Create basic auth header
        auth_string = f"{username}:{password}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        auth_header = f"Basic {encoded_auth}"
        
        # Test authentication by getting user info
        user_response = requests.get(
            f"{url}/wp-json/wp/v2/users/me",
            headers={'Authorization': auth_header}
        )
        
        if user_response.status_code == 200:
            st.session_state.auth_header = auth_header
            st.session_state.authenticated = True
            st.session_state.wp_url = url
            st.session_state.user_info = user_response.json()
            
            # Get available post types
            get_post_types()
            
            return True
        else:
            error_msg = "Authentication failed"
            try:
                error_data = user_response.json()
                if 'message' in error_data:
                    error_msg = f"Authentication failed: {error_data['message']}"
            except:
                error_msg = f"Authentication failed: HTTP {user_response.status_code}"
            
            st.error(error_msg)
            return False
    except Exception as e:
        st.error(f"Error connecting to WordPress site: {str(e)}")
        return False

# Function to get available post types
def get_post_types():
    try:
        response = requests.get(
            f"{st.session_state.wp_url}/wp-json/wp/v2/types",
            headers={'Authorization': st.session_state.auth_header}
        )
        
        if response.status_code == 200:
            types_data = response.json()
            # Filter out non-public or system post types
            filtered_types = {k: v for k, v in types_data.items() 
                             if v.get('rest_base') and k not in ['attachment', 'nav_menu_item', 'wp_block', 'wp_template']}
            st.session_state.post_types = filtered_types
        else:
            st.error("Failed to retrieve post types")
    except Exception as e:
        st.error(f"Error getting post types: {str(e)}")

# Function to get posts of a specific type
def get_posts(post_type):
    try:
        response = requests.get(
            f"{st.session_state.wp_url}/wp-json/wp/v2/{post_type}",
            headers={'Authorization': st.session_state.auth_header}
        )
        
        if response.status_code == 200:
            st.session_state.current_posts = response.json()
            st.session_state.current_post_type = post_type
            return response.json()
        else:
            st.error(f"Failed to retrieve {post_type}")
            return []
    except Exception as e:
        st.error(f"Error getting posts: {str(e)}")
        return []

# Function to get a single post
def get_post(post_type, post_id):
    try:
        response = requests.get(
            f"{st.session_state.wp_url}/wp-json/wp/v2/{post_type}/{post_id}",
            headers={'Authorization': st.session_state.auth_header}
        )
        
        if response.status_code == 200:
            post_data = response.json()
            st.session_state.current_post = post_data
            
            # Extract meta boxes from ACPT data if available
            if 'acpt' in post_data and 'meta' in post_data['acpt']:
                st.session_state.meta_boxes = post_data['acpt']['meta']
            
            return post_data
        else:
            st.error(f"Failed to retrieve post: {response.status_code}")
            try:
                error_data = response.json()
                if 'message' in error_data:
                    st.error(error_data['message'])
            except:
                pass
            return None
    except Exception as e:
        st.error(f"Error getting post: {str(e)}")
        return None

# Function to create or update a post
def save_post(post_type, post_data, post_id=None):
    try:
        headers = {
            'Authorization': st.session_state.auth_header,
            'Content-Type': 'application/json'
        }
        
        if post_id:  # Update existing post
            url = f"{st.session_state.wp_url}/wp-json/wp/v2/{post_type}/{post_id}"
            response = requests.post(url, headers=headers, data=json.dumps(post_data))
        else:  # Create new post
            url = f"{st.session_state.wp_url}/wp-json/wp/v2/{post_type}"
            response = requests.post(url, headers=headers, data=json.dumps(post_data))
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"Failed to save post: {response.status_code}")
            try:
                error_data = response.json()
                if 'message' in error_data:
                    st.error(error_data['message'])
            except:
                pass
            return None
    except Exception as e:
        st.error(f"Error saving post: {str(e)}")
        return None

# Function to delete a post
def delete_post(post_type, post_id):
    try:
        url = f"{st.session_state.wp_url}/wp-json/wp/v2/{post_type}/{post_id}?force=true"
        response = requests.delete(
            url,
            headers={'Authorization': st.session_state.auth_header}
        )
        
        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to delete post: {response.status_code}")
            try:
                error_data = response.json()
                if 'message' in error_data:
                    st.error(error_data['message'])
            except:
                pass
            return False
    except Exception as e:
        st.error(f"Error deleting post: {str(e)}")
        return False

# Function to render the login form
def render_login_form():
    st.title("WordPress CPT Manager")
    st.subheader("Login with WordPress credentials")
    
    with st.form("login_form"):
        wp_url = st.text_input("WordPress Site URL", placeholder="https://example.com")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password", help="Use your WordPress password or application password")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            if wp_url and username and password:
                authenticate(wp_url, username, password)
            else:
                st.error("Please fill in all fields")
    
    st.info("""
    ### Authentication Help
    
    This app uses WordPress REST API authentication. You have two options:
    
    1. **WordPress Application Password** (Recommended):
       - Go to your WordPress admin → Users → Profile
       - Scroll down to "Application Passwords"
       - Create a new application password for "CPT Manager"
       - Use this password instead of your regular WordPress password
    
    2. **Basic Authentication**:
       - If your site has Basic Auth enabled, you can use your regular WordPress credentials
       - Note: This is less secure and may not work on all WordPress installations
    """)

# Function to render the sidebar
def render_sidebar():
    with st.sidebar:
        st.title("Navigation")
        
        # User info
        if st.session_state.user_info:
            st.write(f"Logged in as: {st.session_state.user_info.get('name', 'User')}")
            st.write(f"Site: {st.session_state.wp_url}")
        
        # Navigation buttons
        if st.button("Dashboard", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.session_state.current_post = None
        
        # Post types section
        st.subheader("Content Types")
        
        for post_type, type_data in st.session_state.post_types.items():
            if st.button(f"{type_data.get('name', post_type)}", key=f"nav_{post_type}", use_container_width=True):
                st.session_state.current_page = "post_list"
                st.session_state.current_post = None
                get_posts(post_type)
        
        # Logout button
        if st.button("Logout", type="primary", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

# Function to render the dashboard
def render_dashboard():
    st.title("Dashboard")
    st.write(f"Welcome to the WordPress CPT Manager for {st.session_state.wp_url}")
    
    # Display stats
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Content Types")
        for post_type, type_data in st.session_state.post_types.items():
            st.write(f"- {type_data.get('name', post_type)}")
    
    with col2:
        st.subheader("Quick Actions")
        for post_type, type_data in st.session_state.post_types.items():
            if st.button(f"Create new {type_data.get('name', post_type)}", key=f"create_{post_type}"):
                st.session_state.current_page = "post_edit"
                st.session_state.current_post_type = post_type
                st.session_state.current_post = None
                st.rerun()

# Function to render the post list
def render_post_list():
    post_type = st.session_state.current_post_type
    type_info = st.session_state.post_types.get(post_type, {})
    
    st.title(f"{type_info.get('name', post_type)} List")
    
    # Add new button
    if st.button(f"Add New {type_info.get('name', post_type)}", type="primary"):
        st.session_state.current_page = "post_edit"
        st.session_state.current_post = None
        st.rerun()
    
    # Display posts in a table
    if st.session_state.current_posts:
        for post in st.session_state.current_posts:
            title = post.get('title', {}).get('rendered', 'Untitled')
            date = datetime.fromisoformat(post.get('date', '').replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            status = post.get('status', 'draft')
            
            # Create action buttons
            col1, col2, col3 = st.columns([3, 1, 2])
            with col1:
                st.write(f"**{title}**")
            with col2:
                st.write(f"Status: {status}")
            with col3:
                edit_col, delete_col = st.columns(2)
                with edit_col:
                    if st.button("Edit", key=f"edit_{post['id']}"):
                        st.session_state.current_page = "post_edit"
                        get_post(post_type, post['id'])
                        st.experimental_rerun()
                with delete_col:
                    if st.button("Delete", key=f"delete_{post['id']}"):
                        if delete_post(post_type, post['id']):
                            st.success(f"Post '{title}' deleted successfully")
                            get_posts(post_type)
                            st.rerun()
            
            st.divider()
    else:
        st.info(f"No {type_info.get('name', post_type)} found")

# Function to render the post edit form
def render_post_edit():
    post_type = st.session_state.current_post_type
    type_info = st.session_state.post_types.get(post_type, {})
    current_post = st.session_state.current_post
    
    if current_post:
        st.title(f"Edit {type_info.get('name', post_type)}")
        post_id = current_post.get('id')
        title = current_post.get('title', {}).get('rendered', '')
        content = current_post.get('content', {}).get('rendered', '')
    else:
        st.title(f"Add New {type_info.get('name', post_type)}")
        post_id = None
        title = ""
        content = ""
    
    # Create form
    with st.form(key=f"edit_form_{post_id or 'new'}"):
        # Basic fields
        new_title = st.text_input("Title", value=title)
        new_content = st.text_area("Content", value=content, height=200)
        
        # Status selection
        status_options = ["draft", "publish", "pending", "private"]
        new_status = st.selectbox(
            "Status", 
            options=status_options,
            index=status_options.index(current_post.get('status', 'draft')) if current_post else 0
        )
        
        # ACPT Meta fields
        st.subheader("Custom Fields")
        
        acpt_meta = []
        
        # If editing, get existing meta boxes
        meta_boxes = []
        if current_post and 'acpt' in current_post and 'meta' in current_post['acpt']:
            meta_boxes = current_post['acpt']['meta']
        
        # Render meta boxes and fields
        for meta_box in meta_boxes:
            box_name = meta_box.get('meta_box', '')
            st.write(f"**{box_name}**")
            
            for field in meta_box.get('meta_fields', []):
                field_name = field.get('name', '')
                field_type = field.get('type', 'Text')
                field_value = field.get('value', '')
                field_options = field.get('options', [])
                
                # Render different field types
                new_value = None
                
                if field_type == 'Text':
                    new_value = st.text_input(f"{field_name}", value=field_value, key=f"{box_name}_{field_name}")
                elif field_type == 'Textarea':
                    new_value = st.text_area(f"{field_name}", value=field_value, key=f"{box_name}_{field_name}")
                elif field_type == 'Select':
                    options = [opt.get('value', '') for opt in field_options]
                    default_idx = options.index(field_value) if field_value in options else 0
                    new_value = st.selectbox(f"{field_name}", options=options, index=default_idx, key=f"{box_name}_{field_name}")
                elif field_type == 'Checkbox':
                    new_value = st.checkbox(f"{field_name}", value=bool(field_value), key=f"{box_name}_{field_name}")
                elif field_type == 'Number':
                    new_value = st.number_input(f"{field_name}", value=float(field_value) if field_value else 0, key=f"{box_name}_{field_name}")
                
                # Add to acpt_meta for saving
                if new_value is not None:
                    acpt_meta.append({
                        "box": box_name,
                        "field": field_name,
                        "value": new_value
                    })
        
        # Submit button
        submit = st.form_submit_button("Save")
        
        if submit:
            # Prepare post data
            post_data = {
                "title": new_title,
                "content": new_content,
                "status": new_status
            }
            
            # Add ACPT meta if available
            if acpt_meta:
                post_data["acpt"] = {
                    "meta": acpt_meta
                }
            
            # Save post
            result = save_post(post_type, post_data, post_id)
            
            if result:
                st.success(f"{type_info.get('name', post_type)} saved successfully")
                # Refresh post list
                get_posts(post_type)
                # Go back to post list
                st.session_state.current_page = "post_list"
                st.rerun()
    
    # Cancel button
    if st.button("Cancel"):
        st.session_state.current_page = "post_list"
        st.rerun()

# Main app logic
def main():
    if not st.session_state.authenticated:
        render_login_form()
    else:
        render_sidebar()
        
        # Render the appropriate page based on current_page
        if st.session_state.current_page == "dashboard":
            render_dashboard()
        elif st.session_state.current_page == "post_list":
            render_post_list()
        elif st.session_state.current_page == "post_edit":
            render_post_edit()

if __name__ == "__main__":
    main()

print("WordPress CPT Manager with ACPT integration is running!")
