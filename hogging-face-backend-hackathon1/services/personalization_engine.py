from typing import List, Dict, Any, Optional, Tuple
import logging
from enum import Enum
from functools import lru_cache
import hashlib
import json
import time
from datetime import datetime


class ExperienceLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class PersonalizationSettings:
    """
    Model representing user's personalization settings and preferences.
    """

    def __init__(self, user_id: str, complexity_level: str = 'intermediate',
                 preferred_examples: List[str] = None, focus_areas: List[str] = None,
                 enabled_features: Dict[str, bool] = None, created_at: str = None,
                 updated_at: str = None):
        self.id = f"prefs_{user_id}"
        self.user_id = user_id
        self.complexity_level = complexity_level
        self.preferred_examples = preferred_examples or []
        self.focus_areas = focus_areas or []
        self.enabled_features = enabled_features or {
            'adaptiveDifficulty': True,
            'customExamples': True,
            'terminologyAdjustment': True
        }
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the settings object to a dictionary."""
        return {
            'id': self.id,
            'userId': self.user_id,
            'complexityLevel': self.complexity_level,
            'preferredExamples': self.preferred_examples,
            'focusAreas': self.focus_areas,
            'enabledFeatures': self.enabled_features,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalizationSettings':
        """Create a PersonalizationSettings object from a dictionary."""
        return cls(
            user_id=data.get('userId'),
            complexity_level=data.get('complexityLevel', 'intermediate'),
            preferred_examples=data.get('preferredExamples', []),
            focus_areas=data.get('focusAreas', []),
            enabled_features=data.get('enabledFeatures', {
                'adaptiveDifficulty': True,
                'customExamples': True,
                'terminologyAdjustment': True
            }),
            created_at=data.get('createdAt'),
            updated_at=data.get('updatedAt')
        )

    def validate(self) -> bool:
        """Validate the personalization settings."""
        valid_levels = ['beginner', 'intermediate', 'advanced', 'expert']
        if self.complexity_level not in valid_levels:
            return False

        if not isinstance(self.preferred_examples, list):
            return False

        if not isinstance(self.focus_areas, list):
            return False

        if not isinstance(self.enabled_features, dict):
            return False

        return True


class UserPreferenceHistory:
    """
    Model representing the history of changes to user's personalization preferences.
    """

    def __init__(self, user_id: str, setting_changed: str, old_value: Any, new_value: Any,
                 triggered_by: str = 'user-action', changed_at: str = None):
        self.id = f"hist_{user_id}_{int(time.time())}"  # Simple ID generation
        self.user_id = user_id
        self.setting_changed = setting_changed
        self.old_value = old_value
        self.new_value = new_value
        self.triggered_by = triggered_by
        self.changed_at = changed_at or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the history record to a dictionary."""
        return {
            'id': self.id,
            'userId': self.user_id,
            'settingChanged': self.setting_changed,
            'oldValue': self.old_value,
            'newValue': self.new_value,
            'triggeredBy': self.triggered_by,
            'changedAt': self.changed_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferenceHistory':
        """Create a UserPreferenceHistory object from a dictionary."""
        return cls(
            user_id=data.get('userId'),
            setting_changed=data.get('settingChanged'),
            old_value=data.get('oldValue'),
            new_value=data.get('newValue'),
            triggered_by=data.get('triggeredBy', 'user-action'),
            changed_at=data.get('changedAt')
        )


class PersonalizationEngine:
    """
    Engine to personalize content based on user's background information.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Simple in-memory cache
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes in seconds

    def _generate_cache_key(self, user_profile: Dict[str, Any], content_list: List[Dict[str, Any]]) -> str:
        """
        Generate a cache key based on user profile and content list.
        """
        profile_str = json.dumps(user_profile, sort_keys=True)
        content_str = json.dumps(content_list, sort_keys=True)
        combined = f"{profile_str}|{content_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str):
        """
        Get result from cache if it exists and is not expired.
        """
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            # Check if cache is still valid (not expired)
            if (time.time() - timestamp) < self._cache_ttl:
                self.logger.debug(f"Cache hit for key: {cache_key[:8]}...")
                return result
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        return None

    def _set_in_cache(self, cache_key: str, result):
        """
        Store result in cache with current timestamp.
        """
        self._cache[cache_key] = (result, time.time())
        self.logger.debug(f"Cache set for key: {cache_key[:8]}...")

    def calculate_relevance_score(self, user_profile: Dict[str, Any], content: Dict[str, Any]) -> float:
        """
        Calculate relevance score between user profile and content.

        Args:
            user_profile: User's background information
            content: Content to evaluate

        Returns:
            Relevance score between 0 and 1
        """
        self.logger.debug(f"Calculating relevance score for user profile keys: {list(user_profile.keys())} and content keys: {list(content.keys())}")

        score = 0.0
        total_weight = 0.0

        # Content level matching (30% weight)
        content_level = content.get('level', '').lower()
        user_software_level = user_profile.get('softwareExperienceLevel', '').lower()
        user_hardware_level = user_profile.get('hardwareExperienceLevel', '').lower()

        if content_level and (content_level == user_software_level or content_level == user_hardware_level):
            score += 0.3
            self.logger.debug(f"Content level '{content_level}' matches user level '{user_software_level or user_hardware_level}'")
        elif self._is_level_appropriate(content_level, user_software_level) or self._is_level_appropriate(content_level, user_hardware_level):
            score += 0.15  # Partial match for adjacent levels
            self.logger.debug(f"Content level '{content_level}' is appropriate for user level '{user_software_level or user_hardware_level}'")
        total_weight += 0.3

        # Technical skill matching (40% weight)
        user_skills = set(user_profile.get('technicalSkills', []) or [])
        content_tags = set(content.get('tags', []) or [])

        if user_skills and content_tags:
            matching_skills = user_skills.intersection(content_tags)
            if matching_skills:
                skill_score = len(matching_skills) / max(len(user_skills), len(content_tags))
                score += 0.4 * skill_score
                self.logger.debug(f"Found {len(matching_skills)} matching skills out of {max(len(user_skills), len(content_tags))} possible")
        total_weight += 0.4

        # Development environment matching (20% weight)
        user_envs = set(user_profile.get('preferredDevelopmentEnvironments', []) or [])
        content_envs = set(content.get('environments', []) or [])

        if user_envs and content_envs:
            matching_envs = user_envs.intersection(content_envs)
            if matching_envs:
                env_score = len(matching_envs) / max(len(user_envs), len(content_envs))
                score += 0.2 * env_score
                self.logger.debug(f"Found {len(matching_envs)} matching environments out of {max(len(user_envs), len(content_envs))} possible")
        total_weight += 0.2

        # Normalize score based on actual weights applied
        if total_weight > 0:
            score = score / total_weight
        else:
            # Default score if no matching criteria
            score = 0.5  # Neutral score
            self.logger.debug("No matching criteria found, using default score of 0.5")

        final_score = min(score, 1.0)  # Ensure score doesn't exceed 1.0
        self.logger.debug(f"Final relevance score: {final_score}")
        return final_score

    def get_chapter_personalization_state(self, user_id: str, chapter_id: str) -> Dict[str, Any]:
        """
        Get the personalization state for a specific user and chapter.

        Args:
            user_id: The ID of the user
            chapter_id: The ID of the chapter

        Returns:
            Dictionary containing the personalization state
        """
        # In a real implementation, this would fetch from a database
        # For now, we'll simulate with a simple in-memory store
        cache_key = f"chapter_personalization_state:{user_id}:{chapter_id}"

        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            import time
            if (time.time() - timestamp) < self._cache_ttl:
                return result
            else:
                # Remove expired cache entry
                del self._cache[cache_key]

        # Default state
        state = {
            'userId': user_id,
            'chapterId': chapter_id,
            'isActive': False,
            'adaptationsApplied': [],
            'overrideSettings': {},
            'lastViewedAt': None,
            'engagementMetrics': {
                'timeSpent': 0,
                'scrollDepth': 0.0,
                'completions': 0,
                'helpRequests': 0
            },
            'createdAt': None
        }

        # Cache the result
        import time
        cache_key = f"chapter_personalization_state:{user_id}:{chapter_id}"
        self._cache[cache_key] = (state, time.time())

        return state

    def update_chapter_personalization_state(self, user_id: str, chapter_id: str,
                                           is_active: bool,
                                           adaptations_applied: List[str] = None,
                                           override_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update the personalization state for a specific user and chapter.

        Args:
            user_id: The ID of the user
            chapter_id: The ID of the chapter
            is_active: Whether personalization is active for this chapter
            adaptations_applied: List of adaptations applied to this chapter
            override_settings: Override settings specific to this chapter

        Returns:
            Updated personalization state
        """
        if adaptations_applied is None:
            adaptations_applied = []
        if override_settings is None:
            override_settings = {}

        state = {
            'userId': user_id,
            'chapterId': chapter_id,
            'isActive': is_active,
            'adaptationsApplied': adaptations_applied,
            'overrideSettings': override_settings,
            'lastViewedAt': json.dumps(None),  # Would be current timestamp in real implementation
            'engagementMetrics': {
                'timeSpent': 0,
                'scrollDepth': 0.0,
                'completions': 0,
                'helpRequests': 0
            },
            'updatedAt': json.dumps(None)
        }

        # Cache the result
        cache_key = f"chapter_personalization_state:{user_id}:{chapter_id}"
        import time
        self._cache[cache_key] = (state, time.time())

        return state

    def _is_level_appropriate(self, content_level: str, user_level: str) -> bool:
        """
        Check if content level is appropriate for user level.
        For example, intermediate content is appropriate for advanced users.
        """
        try:
            content_enum = ExperienceLevel(content_level)
            user_enum = ExperienceLevel(user_level)

            # Define appropriate level relationships
            if user_enum == ExperienceLevel.BEGINNER:
                # Beginners should see beginner content
                return content_enum in [ExperienceLevel.BEGINNER]
            elif user_enum == ExperienceLevel.INTERMEDIATE:
                # Intermediate users can handle beginner and intermediate content
                return content_enum in [ExperienceLevel.BEGINNER, ExperienceLevel.INTERMEDIATE]
            elif user_enum == ExperienceLevel.ADVANCED:
                # Advanced users can handle intermediate and advanced content
                return content_enum in [ExperienceLevel.INTERMEDIATE, ExperienceLevel.ADVANCED]
            elif user_enum == ExperienceLevel.EXPERT:
                # Experts can handle any content level
                return True
            else:
                return False
        except ValueError:
            # If level is not recognized, assume it's appropriate
            return True

    def personalize_content_list(self, user_profile: Dict[str, Any], content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Personalize a list of content based on user profile.

        Args:
            user_profile: User's background information
            content_list: List of content items to personalize

        Returns:
            List of content items with relevance scores, sorted by score
        """
        # Generate cache key
        cache_key = self._generate_cache_key(user_profile, content_list)

        # Try to get from cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result

        scored_content = []

        for content in content_list:
            score = self.calculate_relevance_score(user_profile, content)
            content_copy = content.copy()
            content_copy['relevanceScore'] = score
            scored_content.append(content_copy)

        # Sort by relevance score in descending order
        scored_content.sort(key=lambda x: x['relevanceScore'], reverse=True)

        # Cache the result
        self._set_in_cache(cache_key, scored_content)

        return scored_content

    def get_personalized_content(self, user_profile: Dict[str, Any], all_content: List[Dict[str, Any]],
                                limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        Get personalized content for a user with pagination.

        Args:
            user_profile: User's background information
            all_content: All available content
            limit: Number of items to return
            offset: Offset for pagination

        Returns:
            Dictionary with personalized content and metadata
        """
        personalized = self.personalize_content_list(user_profile, all_content)

        # Apply pagination
        paginated_content = personalized[offset:offset + limit]

        return {
            'content': paginated_content,
            'total': len(personalized),
            'page': (offset // limit) + 1,
            'limit': limit,
            'offset': offset
        }

    def get_content_recommendations(self, user_profile: Dict[str, Any], all_content: List[Dict[str, Any]],
                                  count: int = 5) -> List[Dict[str, Any]]:
        """
        Get top content recommendations for a user.

        Args:
            user_profile: User's background information
            all_content: All available content
            count: Number of recommendations to return

        Returns:
            List of top recommended content items
        """
        self.logger.info(f"Getting {count} content recommendations for user with profile keys: {list(user_profile.keys())}")

        personalized = self.personalize_content_list(user_profile, all_content)
        recommendations = personalized[:count]

        # Log metrics about the recommendations
        if recommendations:
            avg_score = sum(item['relevanceScore'] for item in recommendations) / len(recommendations)
            self.logger.info(f"Average relevance score for recommendations: {avg_score:.2f}")
            self.logger.info(f"Top recommendation score: {recommendations[0]['relevanceScore']:.2f}")

        self.logger.info(f"Returning {len(recommendations)} recommendations")
        return recommendations

    def get_chapter_personalization_state(self, user_id: str, chapter_id: str) -> Dict[str, Any]:
        """
        Get the personalization state for a specific user and chapter.

        Args:
            user_id: The ID of the user
            chapter_id: The ID of the chapter

        Returns:
            Dictionary containing the personalization state for the chapter
        """
        # In a real implementation, this would fetch from a database
        # For now, we'll simulate with a simple in-memory store
        cache_key = f"chapter_personalization_state:{user_id}:{chapter_id}"

        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if (time.time() - timestamp) < self._cache_ttl:
                return result
            else:
                # Remove expired cache entry
                del self._cache[cache_key]

        # Default state
        state = {
            'userId': user_id,
            'chapterId': chapter_id,
            'isActive': False,
            'adaptationsApplied': [],
            'overrideSettings': {},
            'lastViewedAt': None,
            'engagementMetrics': {
                'timeSpent': 0,
                'scrollDepth': 0.0,
                'completions': 0,
                'helpRequests': 0
            },
            'createdAt': None
        }

        # Cache the result
        self._cache[cache_key] = (state, time.time())

        return state

    def get_user_personalization_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get the user's global personalization preferences.

        Args:
            user_id: The ID of the user

        Returns:
            Dictionary containing the user's global personalization preferences
        """
        self.logger.info(f"Retrieving personalization preferences for user: {user_id}")

        # In a real implementation, this would fetch from a database
        # For now, we'll simulate with a simple in-memory store
        cache_key = f"user_personalization_prefs:{user_id}"

        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if (time.time() - timestamp) < self._cache_ttl:
                self.logger.debug(f"Cache hit for user preferences: {user_id}")
                return result
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
                self.logger.debug(f"Cache entry expired for user: {user_id}")

        # Create default preferences using the PersonalizationSettings model
        settings = PersonalizationSettings(user_id=user_id)
        prefs = settings.to_dict()

        self.logger.debug(f"Created default preferences for user: {user_id}")

        # Cache the result
        self._cache[cache_key] = (prefs, time.time())
        self.logger.debug(f"Cached preferences for user: {user_id}")

        return prefs

    def update_user_personalization_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the user's global personalization preferences.

        Args:
            user_id: The ID of the user
            preferences: The new preferences to set

        Returns:
            Updated preferences
        """
        self.logger.info(f"Updating personalization preferences for user: {user_id}")

        # Sanitize user input
        sanitized_preferences = self.sanitize_user_input(preferences)

        # Validate preferences
        is_valid, validation_errors = self.validate_preferences(sanitized_preferences)
        if not is_valid:
            error_msg = f"Invalid personalization preferences: {', '.join(validation_errors)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Get current preferences
        current_prefs = self.get_user_personalization_preferences(user_id)

        # Track changes for history
        changes_made = []
        for key, new_value in sanitized_preferences.items():
            old_value = current_prefs.get(key)
            if old_value != new_value:
                changes_made.append({
                    'setting_changed': key,
                    'old_value': old_value,
                    'new_value': new_value
                })
                self.logger.debug(f"Change detected for user {user_id}: {key} changed from {old_value} to {new_value}")

        # Update with new preferences
        updated_data = current_prefs.copy()
        updated_data.update(sanitized_preferences)
        updated_data['updatedAt'] = datetime.now().isoformat()

        # Create a PersonalizationSettings object with the updated data
        settings = PersonalizationSettings(
            user_id=user_id,
            complexity_level=updated_data.get('complexityLevel', 'intermediate'),
            preferred_examples=updated_data.get('preferredExamples', []),
            focus_areas=updated_data.get('focusAreas', []),
            enabled_features=updated_data.get('enabledFeatures', {
                'adaptiveDifficulty': True,
                'customExamples': True,
                'terminologyAdjustment': True
            }),
            created_at=updated_data.get('createdAt'),
            updated_at=updated_data.get('updatedAt')
        )

        # Validate the settings
        if not settings.validate():
            error_msg = "Invalid personalization settings after processing"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Convert to dictionary and cache
        updated_prefs = settings.to_dict()

        # Cache the updated result
        cache_key = f"user_personalization_prefs:{user_id}"
        self._cache[cache_key] = (updated_prefs, time.time())
        self.logger.debug(f"Updated and cached preferences for user: {user_id}")

        # Record changes in history
        for change in changes_made:
            history_record = UserPreferenceHistory(
                user_id=user_id,
                setting_changed=change['setting_changed'],
                old_value=change['old_value'],
                new_value=change['new_value'],
                triggered_by='user-action'
            )
            self._add_to_preference_history(history_record)
            self.logger.debug(f"Recorded preference change for user {user_id}: {change['setting_changed']}")

        return updated_prefs

    def _add_to_preference_history(self, history_record: UserPreferenceHistory):
        """
        Add a preference change to the history.

        Args:
            history_record: The history record to add
        """
        # In a real implementation, this would store in a database
        # For now, we'll simulate with an in-memory store
        if not hasattr(self, '_preference_history'):
            self._preference_history = []

        self._preference_history.append(history_record.to_dict())

        # Keep only the last 100 history items to prevent memory issues
        if len(self._preference_history) > 100:
            self._preference_history = self._preference_history[-100:]

    def export_user_personalization_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all personalization data for a specific user for GDPR compliance.

        Args:
            user_id: The ID of the user

        Returns:
            Dictionary containing all personalization data for the user
        """
        self.logger.info(f"Exporting personalization data for user: {user_id}")

        # Get user preferences
        user_prefs = self.get_user_personalization_preferences(user_id)

        # Get chapter personalization states
        chapter_states = {}
        for key, (state, timestamp) in self._cache.items():
            if key.startswith(f"personalization_state:{user_id}:") and (time.time() - timestamp) < self._cache_ttl:
                # Extract chapter_id from cache key
                chapter_id = key.split(':')[-1]
                chapter_states[chapter_id] = state

        # Get user preference history
        user_history = []
        if hasattr(self, '_preference_history'):
            user_history = [record for record in self._preference_history if record.get('userId') == user_id]

        export_data = {
            'userId': user_id,
            'timestamp': datetime.now().isoformat(),
            'preferences': user_prefs,
            'chapterPersonalizationStates': chapter_states,
            'preferenceHistory': user_history,
            'personalizationSettings': user_prefs  # For backward compatibility
        }

        self.logger.info(f"Exported personalization data for user: {user_id}, containing {len(chapter_states)} chapter states and {len(user_history)} history records")
        return export_data

    def delete_user_personalization_data(self, user_id: str) -> bool:
        """
        Delete all personalization data for a specific user for GDPR compliance.

        Args:
            user_id: The ID of the user

        Returns:
            True if deletion was successful
        """
        self.logger.info(f"Deleting personalization data for user: {user_id}")

        # Remove user preferences from cache
        user_prefs_key = f"user_personalization_prefs:{user_id}"
        if user_prefs_key in self._cache:
            del self._cache[user_prefs_key]
            self.logger.debug(f"Deleted user preferences cache entry for user: {user_id}")

        # Remove chapter personalization states from cache
        keys_to_delete = []
        for key in self._cache.keys():
            if key.startswith(f"personalization_state:{user_id}:"):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._cache[key]
            self.logger.debug(f"Deleted chapter personalization cache entry: {key}")

        # Remove user history from preference history
        if hasattr(self, '_preference_history'):
            self._preference_history = [record for record in self._preference_history if record.get('userId') != user_id]
            self.logger.debug(f"Removed user history records for user: {user_id}")

        self.logger.info(f"Successfully deleted personalization data for user: {user_id}")
        return True

    def reset_chapter_personalization(self, user_id: str, chapter_id: str) -> Dict[str, Any]:
        """
        Reset the personalization state for a specific chapter to default (use global preferences).

        Args:
            user_id: The ID of the user
            chapter_id: The ID of the chapter

        Returns:
            The reset personalization state
        """
        # Get user's global preferences to reset to
        user_prefs = self.get_user_personalization_preferences(user_id)

        # Create a reset state that uses global preferences
        reset_state = {
            'userId': user_id,
            'chapterId': chapter_id,
            'isActive': False,  # Deactivate chapter-specific personalization
            'adaptationsApplied': [],
            'overrideSettings': {},  # No chapter-specific overrides
            'lastViewedAt': None,
            'engagementMetrics': {
                'timeSpent': 0,
                'scrollDepth': 0.0,
                'completions': 0,
                'helpRequests': 0
            },
            'updatedAt': time.time(),
            'usingGlobalPrefs': True  # Indicate that global preferences are being used
        }

        # Cache the reset state
        cache_key = f"chapter_personalization_state:{user_id}:{chapter_id}"
        self._cache[cache_key] = (reset_state, time.time())

        return reset_state

    def update_chapter_personalization_state(self, user_id: str, chapter_id: str,
                                           is_active: bool,
                                           adaptations_applied: List[str] = None,
                                           override_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update the personalization state for a specific user and chapter.

        Args:
            user_id: The ID of the user
            chapter_id: The ID of the chapter
            is_active: Whether personalization is active for this chapter
            adaptations_applied: List of adaptations applied to this chapter
            override_settings: Override settings specific to this chapter

        Returns:
            Updated personalization state
        """
        if adaptations_applied is None:
            adaptations_applied = []
        if override_settings is None:
            override_settings = {}

        state = {
            'userId': user_id,
            'chapterId': chapter_id,
            'isActive': is_active,
            'adaptationsApplied': adaptations_applied,
            'overrideSettings': override_settings,
            'lastViewedAt': None,  # Would be current timestamp in real implementation
            'engagementMetrics': {
                'timeSpent': 0,
                'scrollDepth': 0.0,
                'completions': 0,
                'helpRequests': 0
            },
            'updatedAt': None
        }

        # Cache the result
        cache_key = f"personalization_state:{user_id}:{chapter_id}"
        self._cache[cache_key] = (state, time.time())

        return state

    def update_chapter_specific_preferences(self, user_id: str, chapter_id: str,
                                          preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update personalization preferences for a specific chapter.

        Args:
            user_id: The ID of the user
            chapter_id: The ID of the chapter
            preferences: The new preferences to set for this chapter

        Returns:
            Updated chapter-specific preferences
        """
        # Get the current chapter personalization state
        current_state = self.get_chapter_personalization_state(user_id, chapter_id)

        # Update the override settings with new preferences
        updated_override_settings = current_state.get('overrideSettings', {}).copy()
        updated_override_settings.update(preferences)

        # Update the chapter personalization state with new override settings
        updated_state = self.update_chapter_personalization_state(
            user_id=user_id,
            chapter_id=chapter_id,
            is_active=current_state.get('isActive', False),
            adaptations_applied=current_state.get('adaptationsApplied', []),
            override_settings=updated_override_settings
        )

        return updated_state

    def adapt_content_for_chapter(self, content: str, user_profile: Dict[str, Any],
                                 chapter_id: str = None, override_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Adapt content specifically for a chapter based on user profile and optional overrides.

        Args:
            content: The original content to adapt
            user_profile: User's profile information
            chapter_id: Optional chapter ID for chapter-specific adaptations
            override_settings: Optional settings to override global preferences

        Returns:
            Dictionary containing the adapted content and information about adaptations applied
        """
        if override_settings is None:
            override_settings = {}

        # Get chapter-specific preferences if chapter_id is provided
        chapter_specific_prefs = {}
        if chapter_id:
            chapter_state = self.get_chapter_personalization_state(user_profile.get('userId', 'unknown'), chapter_id)
            chapter_specific_prefs = chapter_state.get('overrideSettings', {})

        # Apply settings in priority order: chapter-specific > override > user profile
        complexity_level = (
            chapter_specific_prefs.get('complexityLevel') or
            override_settings.get('complexityLevel') or
            user_profile.get('complexityLevel') or
            user_profile.get('softwareExperienceLevel') or
            'intermediate'
        )

        preferred_examples = (
            chapter_specific_prefs.get('preferredExamples') or
            override_settings.get('preferredExamples') or
            user_profile.get('preferredExamples') or
            user_profile.get('technicalSkills', [])
        )

        focus_areas = (
            chapter_specific_prefs.get('focusAreas') or
            override_settings.get('focusAreas') or
            user_profile.get('focusAreas', [])
        )

        # Perform content adaptations based on user profile
        adapted_content = content
        adaptations_applied = []

        # Example adaptations - in a real implementation, these would be more sophisticated
        if complexity_level == 'beginner':
            # Simplify complex concepts
            adapted_content = self._simplify_content(adapted_content)
            adaptations_applied.append('simplified-explanation')
        elif complexity_level == 'advanced':
            # Add more depth to explanations
            adapted_content = self._enhance_content(adapted_content)
            adaptations_applied.append('enhanced-explanation')

        # Apply example substitution based on user's technical skills
        if preferred_examples:
            adapted_content = self._substitute_examples(adapted_content, preferred_examples)
            adaptations_applied.append('example-substitution')

        # Apply focus area adjustments
        if focus_areas:
            adapted_content = self._adjust_focus(adapted_content, focus_areas)
            adaptations_applied.append('focus-adjustment')

        return {
            'originalContent': content,
            'adaptedContent': adapted_content,
            'adaptationsApplied': adaptations_applied,
            'relevanceScore': self._calculate_content_relevance(content, user_profile),
            'metadata': {
                'complexityLevel': complexity_level,
                'appliedExamples': preferred_examples,
                'focusAreas': focus_areas
            }
        }

    def _simplify_content(self, content: str) -> str:
        """
        Simplify content for beginner-level users.
        """
        # This is a simplified example - real implementation would be more sophisticated
        # Replace complex technical jargon with simpler explanations
        return content.replace("algorithmic complexity", "how difficult the process is")

    def sanitize_user_input(self, user_input: Any) -> Any:
        """
        Sanitize user input to prevent security issues.
        """
        if isinstance(user_input, str):
            # Remove potentially dangerous characters/sequences
            sanitized = user_input.replace('<script', '&lt;script').replace('javascript:', 'javascript-')
            return sanitized
        elif isinstance(user_input, list):
            return [self.sanitize_user_input(item) for item in user_input]
        elif isinstance(user_input, dict):
            return {key: self.sanitize_user_input(value) for key, value in user_input.items()}
        else:
            return user_input

    def validate_preferences(self, preferences: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate personalization preferences to ensure they meet security and format requirements.

        Args:
            preferences: The preferences to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate complexity level
        complexity_level = preferences.get('complexityLevel')
        if complexity_level is not None:
            valid_levels = ['beginner', 'intermediate', 'advanced', 'expert']
            if complexity_level not in valid_levels:
                errors.append(f"Invalid complexity level: {complexity_level}. Must be one of {valid_levels}")

        # Validate preferred examples
        preferred_examples = preferences.get('preferredExamples')
        if preferred_examples is not None:
            if not isinstance(preferred_examples, list):
                errors.append("preferredExamples must be a list")
            else:
                for example in preferred_examples:
                    if not isinstance(example, str):
                        errors.append(f"Example '{example}' is not a string")
                    elif len(example) > 100:  # Limit length
                        errors.append(f"Example '{example}' exceeds 100 character limit")

        # Validate focus areas
        focus_areas = preferences.get('focusAreas')
        if focus_areas is not None:
            if not isinstance(focus_areas, list):
                errors.append("focusAreas must be a list")
            else:
                for area in focus_areas:
                    if not isinstance(area, str):
                        errors.append(f"Focus area '{area}' is not a string")
                    elif len(area) > 50:  # Limit length
                        errors.append(f"Focus area '{area}' exceeds 50 character limit")

        # Validate enabled features
        enabled_features = preferences.get('enabledFeatures')
        if enabled_features is not None:
            if not isinstance(enabled_features, dict):
                errors.append("enabledFeatures must be a dictionary")
            else:
                for key, value in enabled_features.items():
                    if not isinstance(key, str):
                        errors.append(f"Feature key '{key}' is not a string")
                    elif not isinstance(value, bool):
                        errors.append(f"Feature '{key}' value must be boolean, got {type(value)}")

        return len(errors) == 0, errors

    def _enhance_content(self, content: str) -> str:
        """
        Enhance content for advanced-level users with more depth.
        """
        # Add more technical detail for advanced users
        enhanced = content + "\n\n*Advanced note: This concept can also be implemented using more sophisticated approaches..."
        return enhanced

    def _substitute_examples(self, content: str, preferred_examples: List[str]) -> str:
        """
        Substitute examples in content based on user's preferred examples.
        """
        # In a real implementation, this would match examples to user's skills
        # For now, just return content unchanged
        return content

    def _adjust_focus(self, content: str, focus_areas: List[str]) -> str:
        """
        Adjust content focus based on user's preferred focus areas.
        """
        # In a real implementation, this would emphasize certain topics
        # For now, just return content unchanged
        return content

    def _calculate_content_relevance(self, content: str, user_profile: Dict[str, Any]) -> float:
        """
        Calculate relevance of content to user profile.
        """
        # Use existing relevance calculation logic
        # Create a mock content object to use existing calculation
        mock_content = {
            'level': user_profile.get('softwareExperienceLevel', 'intermediate'),
            'tags': user_profile.get('technicalSkills', []),
            'environments': user_profile.get('preferredDevelopmentEnvironments', [])
        }
        return self.calculate_relevance_score(user_profile, mock_content)