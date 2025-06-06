from IAMApiModule import *
from IAMExceedLMS import Client, get_mapping_fields
from requests import Response, Session

API_GET_USER_RESPONSE = {
    "id": "mock_id",
    "login": "mock_user_name",
    "first_name": "mock_first_name",
    "last_name": "mock_last_name",
    "is_active": True,
    "email": "testdemisto2@paloaltonetworks.com",
}

APP_USER_MANAGER_OUTPUT = {
    "user_id": "12345",
    "user_name": "mock_manager_name",
    "first_name": "mock_first_name",
    "last_name": "mock_last_name",
    "active": "true",
    "email": "testdemistomanager@paloaltonetworks.com",
}

USER_APP_DATA = IAMUserAppData("mock_id", "mock_user_name", is_active=True, app_data=API_GET_USER_RESPONSE)
USER_MANAGER_APP_DATA = IAMUserAppData("12345", "mock_user_name", is_active=True, app_data=APP_USER_MANAGER_OUTPUT)


APP_DISABLED_USER_OUTPUT = {
    "user_id": "mock_id",
    "user_name": "mock_user_name",
    "first_name": "mock_first_name",
    "last_name": "mock_last_name",
    "active": "false",
    "email": "testdemisto2@paloaltonetworks.com",
}

DISABLED_USER_APP_DATA = IAMUserAppData("mock_id", "mock_user_name", is_active=False, app_data=APP_DISABLED_USER_OUTPUT)


def mock_client():
    client = Client(base_url="https://test.com", api_key="test123", verify=False, headers={})
    return client


def get_outputs_from_user_profile(user_profile):
    entry_context = user_profile.to_entry()
    outputs = entry_context.get("Contents")
    return outputs


def test_get_manager_id(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains an email of a user's manager
    When:
        - Calling function get_manager_id
    Then:
        - Ensure the currect manager ID is returned
    """
    client = mock_client()
    user_data = {"manager_email": "testdemistomanager@paloaltonetworks.com"}
    mocker.patch.object(client, "get_user", return_value=USER_MANAGER_APP_DATA)
    id = client.get_manager_id(user_data)
    assert id == "12345"


def test_get_user_command__existing_user(mocker, requests_mock):
    """
    Given:
        - An app client object
        - A user-profile argument that contains an email of a user
    When:
        - The user exists in the application
        - Calling function get_user_command
    Then:
        - Ensure the resulted User Profile object holds the correct user details
    """
    client = mock_client()
    args = {"user-profile": {"email": "testdemisto2@paloaltonetworks.com"}}

    mocker.patch.object(client, "_http_request", return_value=API_GET_USER_RESPONSE)
    mocker.patch.object(IAMUserProfile, "update_with_app_data", return_value={})
    user_profile = IAMCommand(get_user_iam_attrs=["email"]).get_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.GET_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is True
    assert outputs.get("id") == "mock_id"
    assert outputs.get("username") == "mock_user_name"
    assert outputs.get("details", {}).get("first_name") == "mock_first_name"
    assert outputs.get("details", {}).get("last_name") == "mock_last_name"


def test_get_user_command__non_existing_user(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains an email a user
    When:
        - The user does not exist in the application
        - Calling function get_user_command
    Then:
        - Ensure the resulted User Profile object holds information about an unsuccessful result.
    """
    client = mock_client()
    args = {"user-profile": {"email": "testdemisto2@paloaltonetworks.com"}}

    mocker.patch.object(client, "_http_request", return_value=None)

    user_profile = IAMCommand(get_user_iam_attrs=["email"]).get_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.GET_USER
    assert outputs.get("success") is False
    assert outputs.get("errorCode") == IAMErrors.USER_DOES_NOT_EXIST[0]
    assert outputs.get("errorMessage") == IAMErrors.USER_DOES_NOT_EXIST[1]


def test_get_user_command__bad_response(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains an email of a non-existing user in the application
    When:
        - Calling function get_user_command
        - A bad response (500) is returned from the application API
    Then:
        - Ensure the resulted User Profile object holds information about the bad response.
    """
    import demistomock as demisto

    client = mock_client()
    args = {"user-profile": {"email": "testdemisto2@paloaltonetworks.com"}}

    bad_response = Response()
    bad_response.status_code = 500
    bad_response._content = b'{"error": {"detail": "details", "message": "message"}}'

    mocker.patch.object(demisto, "error")
    mocker.patch.object(Session, "request", return_value=bad_response)

    user_profile = IAMCommand(get_user_iam_attrs=["email"]).get_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.GET_USER
    assert outputs.get("success") is False
    assert outputs.get("errorCode") == 500
    assert outputs.get("errorMessage") == "{'detail': 'details', 'message': 'message'}"


def test_create_user_command__success(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains an email of a non-existing user in the application
    When:
        - Calling function create_user_command
    Then:
        - Ensure a User Profile object with the user data is returned
    """
    client = mock_client()
    args = {"user-profile": {"email": "testdemisto2@paloaltonetworks.com"}}

    mocker.patch.object(client, "get_user", return_value=None)
    mocker.patch.object(client, "_http_request", return_value=API_GET_USER_RESPONSE)

    user_profile = IAMCommand(get_user_iam_attrs=["email"]).create_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.CREATE_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is True
    assert outputs.get("id") == "mock_id"
    assert outputs.get("username") == "mock_user_name"
    assert outputs.get("details", {}).get("first_name") == "mock_first_name"
    assert outputs.get("details", {}).get("last_name") == "mock_last_name"


def test_create_user_command__user_already_exists(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains an email of a user
    When:
        - The user already exists in the application and disabled
        - allow-enable argument is false
        - Calling function create_user_command
    Then:
        - Ensure the command is considered successful and the user is still disabled
    """
    client = mock_client()
    args = {"user-profile": {"email": "testdemisto2@paloaltonetworks.com"}, "allow-enable": "false"}

    mocker.patch.object(client, "get_user", return_value=DISABLED_USER_APP_DATA)
    mocker.patch.object(client, "update_user", return_value=DISABLED_USER_APP_DATA)

    user_profile = IAMCommand(get_user_iam_attrs=["email"]).create_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.UPDATE_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is False
    assert outputs.get("id") == "mock_id"
    assert outputs.get("username") == "mock_user_name"
    assert outputs.get("details", {}).get("first_name") == "mock_first_name"
    assert outputs.get("details", {}).get("last_name") == "mock_last_name"


def test_update_user_command__non_existing_user(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains user data
    When:
        - The user does not exist in the application
        - create-if-not-exists parameter is checked
        - Create User command is enabled
        - Calling function update_user_command
    Then:
        - Ensure the create action is executed
        - Ensure a User Profile object with the user data is returned
    """
    client = mock_client()
    args = {"user-profile": {"email": "testdemisto2@paloaltonetworks.com", "givenname": "mock_first_name"}}

    mocker.patch.object(client, "get_user", return_value=None)
    mocker.patch.object(client, "create_user", return_value=USER_APP_DATA)

    user_profile = IAMCommand(create_if_not_exists=True, get_user_iam_attrs=["email"]).update_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.CREATE_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is True
    assert outputs.get("id") == "mock_id"
    assert outputs.get("username") == "mock_user_name"
    assert outputs.get("details", {}).get("first_name") == "mock_first_name"
    assert outputs.get("details", {}).get("last_name") == "mock_last_name"


def test_update_user_command__command_is_disabled(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains user data
    When:
        - Update User command is disabled
        - Calling function update_user_command
    Then:
        - Ensure the command is considered successful and skipped
    """
    client = mock_client()
    args = {"user-profile": {"email": "testdemisto2@paloaltonetworks.com", "givenname": "mock_first_name"}}

    mocker.patch.object(client, "get_user", return_value=None)
    mocker.patch.object(client, "update_user", return_value=USER_APP_DATA)

    user_profile = IAMCommand(is_update_enabled=False, get_user_iam_attrs=["email"]).update_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.UPDATE_USER
    assert outputs.get("success") is True
    assert outputs.get("skipped") is True
    assert outputs.get("reason") == "Command is disabled."


def test_update_user_command__allow_enable(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains user data
    When:
        - The user is disabled in the application
        - allow-enable argument is true
        - Calling function update_user_command
    Then:
        - Ensure the user is enabled at the end of the command execution.
    """
    client = mock_client()
    args = {
        "user-profile": {"email": "testdemisto2@paloaltonetworks.com", "givenname": "mock_first_name"},
        "allow-enable": "true",
    }

    mocker.patch.object(client, "get_user", return_value=DISABLED_USER_APP_DATA)
    mocker.patch.object(client, "update_user", return_value=USER_APP_DATA)

    user_profile = IAMCommand(get_user_iam_attrs=["email"]).update_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.UPDATE_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is True
    assert outputs.get("id") == "mock_id"
    assert outputs.get("username") == "mock_user_name"
    assert outputs.get("details", {}).get("first_name") == "mock_first_name"
    assert outputs.get("details", {}).get("last_name") == "mock_last_name"


def test_disable_user_command__non_existing_user(mocker):
    """
    Given:
        - An app client object
        - A user-profile argument that contains an email of a user
    When:
        - create-if-not-exists parameter is unchecked
        - The user does not exist in the application
        - Calling function disable_user_command
    Then:
        - Ensure the command is considered successful and skipped
    """
    client = mock_client()
    args = {"user-profile": {"email": "testdemisto2@paloaltonetworks.com"}}

    mocker.patch.object(client, "get_user", return_value=None)

    user_profile = IAMCommand(get_user_iam_attrs=["email"]).disable_user(client, args)
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.DISABLE_USER
    assert outputs.get("success") is True
    assert outputs.get("skipped") is True
    assert outputs.get("reason") == IAMErrors.USER_DOES_NOT_EXIST[1]


def test_get_mapping_fields_command(mocker):
    """
    Given:
        - An app client object
    When:
        - User schema in the application contains the fields 'field1' and 'field2'
        - Calling function get_mapping_fields_command
    Then:
        - Ensure a GetMappingFieldsResponse object that contains the application fields is returned
    """
    client = mock_client()
    mocker.patch.object(client, "get_app_fields", return_value={"field1": "desc1", "field2": "desc2"})

    mapping_response = get_mapping_fields(client)
    mapping = mapping_response.extract_mapping()

    assert mapping.get(IAMUserProfile.DEFAULT_INCIDENT_TYPE, {}).get("field1") == "desc1"
    assert mapping.get(IAMUserProfile.DEFAULT_INCIDENT_TYPE, {}).get("field2") == "desc2"
