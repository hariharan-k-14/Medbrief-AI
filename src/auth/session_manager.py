import streamlit as st
from datetime import datetime, timedelta
from config.app_config import SESSION_TIMEOUT_MINUTES
import json

class SessionManager:
    @staticmethod
    def init_session():
        """Initialize or validate session."""
        if 'session_initialized' not in st.session_state:
            st.session_state.session_initialized = True
            # Always clear persistent browser storage on new initialization
            SessionManager._clear_persistent_storage()
            
        if 'auth_service' not in st.session_state:
            from auth.auth_service import AuthService
            st.session_state.auth_service = AuthService()
        
        # Check session timeout
        if 'last_activity' in st.session_state:
            idle_time = datetime.now() - st.session_state.last_activity
            if idle_time > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                SessionManager.clear_session_state()
                st.error("Session expired. Please log in again.")
                st.rerun()
        
        # Update last activity
        st.session_state.last_activity = datetime.now()
        
        # Validate token and user data
        if 'user' in st.session_state:
            user_data = st.session_state.auth_service.validate_session_token()
            if not user_data:
                SessionManager.clear_session_state()
                st.error("Invalid session. Please log in again.")
                st.rerun()
    
    @staticmethod
    def _restore_from_storage():
        """No-op to prevent auto-restoring session across app restarts."""
        pass
    
    @staticmethod
    def _inject_storage_script():
        """Inject JavaScript to ensure localStorage is cleared on session init."""
        storage_script = """
        <script>
        window.addEventListener('DOMContentLoaded', function() {
            localStorage.removeItem('medbrief_auth');
            localStorage.removeItem('medbrief_user');
            localStorage.removeItem('hia_auth');
            localStorage.removeItem('hia_user');
        });
        window.clearAuthData = function() {
            localStorage.removeItem('medbrief_auth');
            localStorage.removeItem('medbrief_user');
            localStorage.removeItem('hia_auth');
            localStorage.removeItem('hia_user');
        };
        </script>
        """
        st.markdown(storage_script, unsafe_allow_html=True)

    @staticmethod
    def clear_session_state():
        """Clear all session state data."""
        # Clear persistent storage
        SessionManager._clear_persistent_storage()
        
        keys_to_keep = ['session_initialized']
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
    
    @staticmethod
    def _clear_persistent_storage():
        """Clear persistent storage."""
        clear_script = """
        <script>
        localStorage.removeItem('medbrief_auth');
        localStorage.removeItem('medbrief_user');
        localStorage.removeItem('hia_auth');
        localStorage.removeItem('hia_user');
        if (typeof window.clearAuthData === 'function') {
            window.clearAuthData();
        }
        </script>
        """
        st.markdown(clear_script, unsafe_allow_html=True)
    
    @staticmethod
    def _save_to_persistent_storage(user_data, auth_token):
        """No-op: Do not save authentication data to persistent storage."""
        pass

    @staticmethod
    def is_authenticated():
        """Check if user is authenticated."""
        return bool(st.session_state.get('user'))
    
    @staticmethod
    def create_chat_session():
        """Create a new chat session."""
        if not SessionManager.is_authenticated():
            return False, "Not authenticated"
        return st.session_state.auth_service.create_session(
            st.session_state.user['id']
        )
    
    @staticmethod
    def get_user_sessions():
        """Get user's chat sessions."""
        if not SessionManager.is_authenticated():
            return False, []
        return st.session_state.auth_service.get_user_sessions(
            st.session_state.user['id']
        )
    
    @staticmethod
    def delete_session(session_id):
        """Delete a chat session."""
        if not SessionManager.is_authenticated():
            return False, "Not authenticated"
        return st.session_state.auth_service.delete_session(session_id)
    
    @staticmethod
    def logout():
        """Logout user and clear session."""
        if 'auth_service' in st.session_state:
            st.session_state.auth_service.sign_out()
        SessionManager.clear_session_state()
    
    @staticmethod
    def login(email, password):
        """Handle user login."""
        if 'auth_service' not in st.session_state:
            from auth.auth_service import AuthService
            st.session_state.auth_service = AuthService()
            
        success, user_data = st.session_state.auth_service.sign_in(email, password)
        return success, user_data
