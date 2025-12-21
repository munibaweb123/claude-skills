import unittest
from personalization_engine import PersonalizationEngine, ExperienceLevel
import json


class TestPersonalizationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = PersonalizationEngine()

    def test_calculate_relevance_score_matching_level(self):
        """Test that matching experience levels get higher scores."""
        user_profile = {
            'softwareExperienceLevel': 'intermediate',
            'hardwareExperienceLevel': 'beginner',
            'technicalSkills': ['python', 'react'],
            'preferredDevelopmentEnvironments': ['vscode']
        }

        content = {
            'level': 'intermediate',
            'tags': ['python', 'django'],
            'environments': ['vscode']
        }

        score = self.engine.calculate_relevance_score(user_profile, content)
        # Should get a relatively high score due to level match and some skill matches
        self.assertGreater(score, 0.5)

    def test_calculate_relevance_score_no_match(self):
        """Test that completely mismatched content gets a low score."""
        user_profile = {
            'softwareExperienceLevel': 'beginner',
            'technicalSkills': ['html', 'css']
        }

        content = {
            'level': 'expert',
            'tags': ['kernel', 'assembly']
        }

        score = self.engine.calculate_relevance_score(user_profile, content)
        # Should get a lower score due to level mismatch and no skill overlap
        self.assertLess(score, 0.5)

    def test_calculate_relevance_score_skill_matching(self):
        """Test that matching technical skills contribute to the score."""
        user_profile = {
            'softwareExperienceLevel': 'intermediate',
            'technicalSkills': ['python', 'react', 'javascript']
        }

        content = {
            'level': 'intermediate',
            'tags': ['python', 'flask']  # One matching skill
        }

        score = self.engine.calculate_relevance_score(user_profile, content)
        # Should get a moderate score due to partial skill match
        self.assertGreater(score, 0.3)

    def test_calculate_relevance_score_environment_matching(self):
        """Test that matching development environments contribute to the score."""
        user_profile = {
            'softwareExperienceLevel': 'intermediate',
            'technicalSkills': ['javascript'],
            'preferredDevelopmentEnvironments': ['vscode', 'intellij']
        }

        content = {
            'level': 'intermediate',
            'tags': ['javascript'],
            'environments': ['vscode']  # Matching environment
        }

        score = self.engine.calculate_relevance_score(user_profile, content)
        # Should get a good score due to environment match
        self.assertGreater(score, 0.6)

    def test_personalize_content_list_sorting(self):
        """Test that content is sorted by relevance score."""
        user_profile = {
            'softwareExperienceLevel': 'intermediate',
            'technicalSkills': ['python']
        }

        content_list = [
            {'id': '1', 'level': 'advanced', 'tags': ['java']},
            {'id': '2', 'level': 'intermediate', 'tags': ['python']},  # Should match
            {'id': '3', 'level': 'beginner', 'tags': ['html']}
        ]

        personalized = self.engine.personalize_content_list(user_profile, content_list)

        # The matching content should be first
        self.assertEqual(personalized[0]['id'], '2')
        # Scores should be in descending order
        for i in range(len(personalized) - 1):
            self.assertGreaterEqual(personalized[i]['relevanceScore'], personalized[i+1]['relevanceScore'])

    def test_get_content_recommendations(self):
        """Test that we get the specified number of recommendations."""
        user_profile = {
            'softwareExperienceLevel': 'intermediate',
            'technicalSkills': ['python', 'javascript']
        }

        content_list = [
            {'id': f'{i}', 'level': 'intermediate', 'tags': ['python' if i % 2 == 0 else 'javascript']}
            for i in range(10)
        ]

        recommendations = self.engine.get_content_recommendations(user_profile, content_list, count=3)

        # Should get exactly 3 recommendations
        self.assertEqual(len(recommendations), 3)

    def test_level_appropriateness(self):
        """Test the _is_level_appropriate helper method through the main calculation."""
        # Beginner user should get lower scores for expert content
        beginner_profile = {
            'softwareExperienceLevel': 'beginner',
            'technicalSkills': ['html']
        }

        expert_content = {
            'level': 'expert',
            'tags': ['kernel', 'assembly']
        }

        score = self.engine.calculate_relevance_score(beginner_profile, expert_content)
        self.assertLess(score, 0.5)

        # Expert user should get higher scores for expert content
        expert_profile = {
            'softwareExperienceLevel': 'expert',
            'technicalSkills': ['kernel', 'assembly']
        }

        score = self.engine.calculate_relevance_score(expert_profile, expert_content)
        self.assertGreater(score, 0.3)  # Even without skill matches, expert should handle expert content

    def test_cache_functionality(self):
        """Test that caching works correctly."""
        user_profile = {
            'softwareExperienceLevel': 'intermediate',
            'technicalSkills': ['python']
        }

        content_list = [
            {'id': '1', 'level': 'intermediate', 'tags': ['python']}
        ]

        # Get personalized content for the first time
        result1 = self.engine.personalize_content_list(user_profile, content_list)

        # Get it again with the same inputs (should use cache)
        result2 = self.engine.personalize_content_list(user_profile, content_list)

        # Results should be identical
        self.assertEqual(result1[0]['relevanceScore'], result2[0]['relevanceScore'])


class TestChapterPersonalization(unittest.TestCase):
    def setUp(self):
        self.engine = PersonalizationEngine()

    def test_get_chapter_personalization_state_default(self):
        """Test that getting chapter personalization state returns default values for new user/chapter."""
        user_id = "test-user-123"
        chapter_id = "test-chapter-456"

        state = self.engine.get_chapter_personalization_state(user_id, chapter_id)

        self.assertEqual(state['userId'], user_id)
        self.assertEqual(state['chapterId'], chapter_id)
        self.assertFalse(state['isActive'])
        self.assertEqual(state['adaptationsApplied'], [])
        self.assertEqual(state['overrideSettings'], {})
        self.assertIsNone(state['lastViewedAt'])
        self.assertEqual(state['engagementMetrics']['timeSpent'], 0)
        self.assertEqual(state['engagementMetrics']['scrollDepth'], 0.0)

    def test_update_chapter_personalization_state(self):
        """Test updating chapter personalization state."""
        user_id = "test-user-123"
        chapter_id = "test-chapter-456"
        is_active = True
        adaptations = ["simplified-explanation", "practical-examples"]
        override_settings = {"complexity": "beginner", "focus": "practical"}

        updated_state = self.engine.update_chapter_personalization_state(
            user_id, chapter_id, is_active, adaptations, override_settings
        )

        self.assertEqual(updated_state['userId'], user_id)
        self.assertEqual(updated_state['chapterId'], chapter_id)
        self.assertTrue(updated_state['isActive'])
        self.assertEqual(updated_state['adaptationsApplied'], adaptations)
        self.assertEqual(updated_state['overrideSettings'], override_settings)

    def test_get_user_personalization_preferences_default(self):
        """Test that getting user preferences returns default values."""
        user_id = "test-user-123"

        prefs = self.engine.get_user_personalization_preferences(user_id)

        self.assertEqual(prefs['userId'], user_id)
        self.assertEqual(prefs['complexityLevel'], 'intermediate')
        self.assertEqual(prefs['preferredExamples'], [])
        self.assertEqual(prefs['focusAreas'], [])
        self.assertIsNotNone(prefs['enabledFeatures'])
        self.assertIsNone(prefs['updatedAt'])

    def test_update_user_personalization_preferences(self):
        """Test updating user personalization preferences."""
        user_id = "test-user-123"
        new_prefs = {
            'complexityLevel': 'advanced',
            'preferredExamples': ['real-world', 'case-study'],
            'focusAreas': ['performance', 'optimization'],
            'enabledFeatures': {
                'adaptiveDifficulty': True,
                'customExamples': False,
                'terminologyAdjustment': True
            }
        }

        updated_prefs = self.engine.update_user_personalization_preferences(user_id, new_prefs)

        self.assertEqual(updated_prefs['userId'], user_id)
        self.assertEqual(updated_prefs['complexityLevel'], 'advanced')
        self.assertEqual(updated_prefs['preferredExamples'], ['real-world', 'case-study'])
        self.assertEqual(updated_prefs['focusAreas'], ['performance', 'optimization'])
        self.assertEqual(updated_prefs['enabledFeatures']['customExamples'], False)

    def test_reset_chapter_personalization(self):
        """Test resetting chapter personalization to default state."""
        user_id = "test-user-123"
        chapter_id = "test-chapter-456"

        # First set up a personalized state
        self.engine.update_chapter_personalization_state(
            user_id, chapter_id, True, ["simplified-explanation"], {"complexity": "beginner"}
        )

        # Reset the chapter personalization
        reset_state = self.engine.reset_chapter_personalization(user_id, chapter_id)

        self.assertEqual(reset_state['userId'], user_id)
        self.assertEqual(reset_state['chapterId'], chapter_id)
        self.assertFalse(reset_state['isActive'])  # Should be deactivated after reset
        self.assertEqual(reset_state['adaptationsApplied'], [])
        self.assertEqual(reset_state['overrideSettings'], {})  # Settings cleared
        self.assertTrue(reset_state['usingGlobalPrefs'])  # Should indicate using global prefs


class TestContentAdaptation(unittest.TestCase):
    def setUp(self):
        self.engine = PersonalizationEngine()

    def test_adapt_content_for_chapter_beginner(self):
        """Test content adaptation for beginner-level users."""
        content = "This section covers algorithmic complexity in detail."
        user_profile = {
            'softwareExperienceLevel': 'beginner',
            'technicalSkills': ['basic-programming']
        }

        adapted_result = self.engine.adapt_content_for_chapter(content, user_profile)

        # The adapted content should have simplified explanations
        self.assertIn('originalContent', adapted_result)
        self.assertIn('adaptedContent', adapted_result)
        self.assertIn('adaptationsApplied', adapted_result)
        self.assertGreaterEqual(adapted_result['relevanceScore'], 0)
        self.assertLessEqual(adapted_result['relevanceScore'], 1)

    def test_adapt_content_for_chapter_advanced(self):
        """Test content adaptation for advanced-level users."""
        content = "This section covers basic programming concepts."
        user_profile = {
            'softwareExperienceLevel': 'advanced',
            'technicalSkills': ['python', 'java', 'go', 'react']
        }

        adapted_result = self.engine.adapt_content_for_chapter(content, user_profile)

        # Should have applied enhancements for advanced user
        self.assertIn('originalContent', adapted_result)
        self.assertIn('adaptedContent', adapted_result)
        self.assertGreaterEqual(adapted_result['relevanceScore'], 0)
        self.assertLessEqual(adapted_result['relevanceScore'], 1)

    def test_adapt_content_with_overrides(self):
        """Test content adaptation with chapter-specific overrides."""
        content = "This section explains how to use various development tools."
        user_profile = {
            'softwareExperienceLevel': 'intermediate',
            'technicalSkills': ['javascript', 'react']
        }
        override_settings = {
            'complexityLevel': 'beginner',
            'preferredExamples': ['simple', 'basic']
        }

        adapted_result = self.engine.adapt_content_for_chapter(content, user_profile,
                                                              chapter_id="test-chapter",
                                                              override_settings=override_settings)

        # Should apply overrides instead of user profile defaults
        self.assertIn('originalContent', adapted_result)
        self.assertIn('adaptedContent', adapted_result)
        self.assertIn('adaptationsApplied', adapted_result)


if __name__ == '__main__':
    unittest.main()