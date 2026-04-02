"""
Unit and integration tests for Mergington High School API endpoints.
Tests use the AAA (Arrange-Act-Assert) pattern for clarity and maintainability.
"""

import pytest
from fastapi.testclient import TestClient
from copy import deepcopy
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities as app_activities


@pytest.fixture
def client():
    """Fixture providing a TestClient for the FastAPI application."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities(activities_fixture):
    """
    Fixture that resets the in-memory activities database before each test.
    This ensures test isolation by providing a fresh state.
    """
    global app_activities
    # Store original state
    original = deepcopy(app_activities)
    
    # Reset to fixture state
    app_activities.clear()
    app_activities.update(deepcopy(activities_fixture))
    
    yield
    
    # Cleanup: restore original state
    app_activities.clear()
    app_activities.update(original)


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client, activities_fixture):
        """
        ARRANGE: Set up test client and expected activities count
        ACT: Call GET /activities
        ASSERT: Verify all 9 activities are returned
        """
        # Arrange
        expected_count = len(activities_fixture)
        
        # Act
        response = client.get("/activities")
        
        # Assert
        assert response.status_code == 200
        assert len(response.json()) == expected_count

    def test_get_activities_returns_correct_structure(self, client):
        """
        ARRANGE: Define required keys for activity objects
        ACT: Call GET /activities and inspect first activity
        ASSERT: Verify each activity has required structure
        """
        # Arrange
        required_keys = {"description", "schedule", "max_participants", "participants"}
        
        # Act
        response = client.get("/activities")
        activities = response.json()
        
        # Assert
        assert response.status_code == 200
        for activity_name, activity_data in activities.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_data, dict)
            assert required_keys == set(activity_data.keys()), \
                f"Activity '{activity_name}' missing or has extra keys"

    def test_get_activities_returns_correct_data(self, client, activities_fixture):
        """
        ARRANGE: Prepare expected activities data
        ACT: Call GET /activities
        ASSERT: Verify returned data matches expected values
        """
        # Arrange
        expected_activities = activities_fixture
        
        # Act
        response = client.get("/activities")
        returned_activities = response.json()
        
        # Assert
        assert response.status_code == 200
        assert returned_activities == expected_activities

    def test_get_activities_participants_is_list(self, client):
        """
        ARRANGE: Set up expectation that participants should be a list
        ACT: Call GET /activities
        ASSERT: Verify participants field is a list for all activities
        """
        # Arrange (no setup needed)
        
        # Act
        response = client.get("/activities")
        activities = response.json()
        
        # Assert
        for activity_name, activity_data in activities.items():
            assert isinstance(activity_data["participants"], list), \
                f"Participants for '{activity_name}' should be a list"


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_new_student_success(self, client, activities_fixture):
        """
        ARRANGE: Set up a new student email and existing activity
        ACT: Sign up the student for an activity
        ASSERT: Verify signup succeeds and participant is added
        """
        # Arrange
        activity_name = "Chess Club"
        new_student_email = "newstudent@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_student_email}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {new_student_email} for {activity_name}"
        assert new_student_email in app_activities[activity_name]["participants"]

    def test_signup_activity_not_found(self, client):
        """
        ARRANGE: Set up a non-existent activity name and student email
        ACT: Attempt to sign up for non-existent activity
        ASSERT: Verify 404 error is returned
        """
        # Arrange
        non_existent_activity = "Nonexistent Activity"
        student_email = "student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{non_existent_activity}/signup",
            params={"email": student_email}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_student_already_signed_up(self, client):
        """
        ARRANGE: Set up an existing student already in an activity
        ACT: Attempt to sign up the same student again
        ASSERT: Verify 400 error is returned
        """
        # Arrange
        activity_name = "Chess Club"
        existing_student = "michael@mergington.edu"  # Already in Chess Club
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": existing_student}
        )
        
        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up"

    def test_signup_updates_participants_list(self, client):
        """
        ARRANGE: Set up a new student and target activity
        ACT: Sign up student and check participant count
        ASSERT: Verify participant count increased by 1
        """
        # Arrange
        activity_name = "Programming Class"
        new_student = "alice@mergington.edu"
        initial_count = len(app_activities[activity_name]["participants"])
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_student}
        )
        final_count = len(app_activities[activity_name]["participants"])
        
        # Assert
        assert response.status_code == 200
        assert final_count == initial_count + 1

    def test_signup_response_message_format(self, client):
        """
        ARRANGE: Set up student and activity details
        ACT: Sign up student and capture response message
        ASSERT: Verify message format is correct
        """
        # Arrange
        activity_name = "Drama Club"
        student_email = "bob@mergington.edu"
        expected_message = f"Signed up {student_email} for {activity_name}"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": student_email}
        )
        message = response.json().get("message")
        
        # Assert
        assert response.status_code == 200
        assert message == expected_message

    def test_signup_multiple_students_same_activity(self, client):
        """
        ARRANGE: Set up multiple different students for same activity
        ACT: Sign up each student sequentially
        ASSERT: Verify all students are added without error
        """
        # Arrange
        activity_name = "Science Club"
        students = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        # Act & Assert for each student
        for student_email in students:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": student_email}
            )
            assert response.status_code == 200
            assert student_email in app_activities[activity_name]["participants"]

    def test_signup_case_sensitive_activity_name(self, client):
        """
        ARRANGE: Set up test with different case variations of activity name
        ACT: Attempt signup with incorrect case
        ASSERT: Verify 404 error (activity name is case-sensitive)
        """
        # Arrange
        correct_name = "Chess Club"
        incorrect_case = "chess club"  # lowercase
        student_email = "student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{incorrect_case}/signup",
            params={"email": student_email}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
