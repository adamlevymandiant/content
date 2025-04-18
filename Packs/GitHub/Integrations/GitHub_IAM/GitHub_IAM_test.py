import demistomock as demisto
import pytest
from GitHub_IAM import Client, IAMUserProfile, create_user_command, get_user_command, update_user_command
from IAMApiModule import *
from requests import Session
from requests.models import Response

BASE_MOCK_URL = "https://test.com"
MOCK_ORG = "test123"


def mock_client():
    client = Client(base_url=BASE_MOCK_URL, org=MOCK_ORG, verify=False, headers={})
    return client


create_inp_schme = {"familyName": "J13", "givenName": "MJ", "userName": "TestID@networks.com", "emails": "TestID@networks.com"}

demisto.callingContext = {"context": {"IntegrationInstance": "Test", "IntegrationBrand": "Test"}}

GITHUB_CREATE_USER_OUTPUT = {
    "emails": [{"value": "TestID@networks.com", "type": "work", "primary": True}],
    "roles": [],
    "userName": "TestID@networks.com",
    "name": {"givenName": "MJ", "familyName": "J13"},
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "id": "12345",
    "active": True,
    "meta": {
        "resourceType": "User",
        "created": "2020-11-23T09:26:31.000-08:00",
        "lastModified": "2020-11-23T09:26:31.000-08:00",
        "location": "https://api.github.com/scim/v2/abc",
    },
}

GITHUB_UPDATE_USER_OUTPUT = {
    "schemas": ["urn:ietf:paramsListResponse"],
    "totalResults": 1,
    "itemsPerPage": 1,
    "startIndex": 1,
    "Resources": [
        {
            "emails": [{"value": "TestID@networks.com", "type": "work", "primary": True}],
            "roles": [],
            "name": {"familyName": "J13", "givenName": "MJ"},
            "userName": "TestID@networks.com",
            "schemas": ["urn:ietf:User"],
            "id": "12345",
            "active": True,
            "meta": {
                "resourceType": "User",
                "created": "2020-11-23T09:26:31.000-08:00",
                "lastModified": "2020-11-23T09:26:31.000-08:00",
                "location": "//l",
            },
        }
    ],
}


def get_outputs_from_user_profile(user_profile):
    entry_context = user_profile.to_entry()
    outputs = entry_context.get("Contents")

    return outputs


def test_create_user_command(mocker):
    args = {"user-profile": {"emails": "mock@mock.com"}}
    client = mock_client()

    mocker.patch.object(client, "create_user", return_value=GITHUB_CREATE_USER_OUTPUT)
    mocker.patch.object(client, "get_user", return_value={"totalResults": 0})

    iam_user_profile = create_user_command(client, args, "mapper_out", True, True)
    outputs = get_outputs_from_user_profile(iam_user_profile)

    assert outputs.get("action") == IAMActions.CREATE_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is True
    assert outputs.get("id") == "12345"
    assert outputs.get("username") == "TestID@networks.com"


def test_get_user_command__existing_user(mocker):
    client = mock_client()
    args = {"user-profile": {"emails": "mock@mock.com"}}

    mocker.patch.object(client, "get_user", return_value=GITHUB_UPDATE_USER_OUTPUT)
    mocker.patch.object(IAMUserProfile, "update_with_app_data", return_value={})

    iam_user_profile = get_user_command(client, args, "mapper_in", "mapper_out")
    outputs = get_outputs_from_user_profile(iam_user_profile)

    assert outputs.get("action") == IAMActions.GET_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is True
    assert outputs.get("id") == "12345"
    assert outputs.get("username") == "TestID@networks.com"


@pytest.mark.parametrize(
    "args, mock_url",
    [
        (
            {"user-profile": {"emails": "mock@mock.com"}},
            f'{BASE_MOCK_URL}/scim/v2/organizations/{MOCK_ORG}/Users?filter=emails eq "mock@mock.com"',
        ),
        (
            {"user-profile": {"userName": "TestID@networks.com", "emails": "mock@mock.com"}},
            f'{BASE_MOCK_URL}/scim/v2/organizations/{MOCK_ORG}/Users?filter=userName eq "TestID@networks.com"',
        ),
        (
            {"user-profile": {"id": 12345, "userName": "TestID@networks.com", "emails": "mock@mock.com"}},
            f'{BASE_MOCK_URL}/scim/v2/organizations/{MOCK_ORG}/Users?filter=id eq "12345"',
        ),
    ],
)
def test_get_user_command_by_order(mocker, args, mock_url, requests_mock):
    """
    Given:
    - Cortex XSOAR arguments.

    When:
    - Executing get-user command.
    Cases:
    case a: User profile has email data.
    case b: User profile has email and username data.
    case c: User profile has email, username and id data.

    Then:
    - Ensure expected data is returned, and expected mocked URL is called.
    """
    client = mock_client()
    requests_mock.get(mock_url, json=GITHUB_UPDATE_USER_OUTPUT)
    mocker.patch.object(IAMUserProfile, "update_with_app_data", return_value={})

    iam_user_profile = get_user_command(client, args, "mapper_in", "mapper_out")
    outputs = get_outputs_from_user_profile(iam_user_profile)

    assert outputs.get("action") == IAMActions.GET_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is True
    assert outputs.get("id") == "12345"
    assert outputs.get("username") == "TestID@networks.com"


def test_get_user_command__non_existing_user(mocker):
    client = mock_client()
    args = {"user-profile": {"emails": "mock@mock.com"}}

    mocker.patch.object(client, "get_user", return_value={})

    iam_user_profile = get_user_command(client, args, "mapper_in", "mapper_out")
    outputs = get_outputs_from_user_profile(iam_user_profile)

    assert outputs.get("action") == IAMActions.GET_USER
    assert outputs.get("success") is False
    assert outputs.get("errorCode") == IAMErrors.USER_DOES_NOT_EXIST[0]
    assert outputs.get("errorMessage") == IAMErrors.USER_DOES_NOT_EXIST[1]


def test_get_user_command__bad_response(mocker):
    client = mock_client()
    args = {"user-profile": {"emails": "mock@mock.com"}}

    bad_response = Response()
    bad_response.status_code = 500
    bad_response._content = b'{"errorCode": "mock_error_code", "errorSummary": "mock_error_summary", "message": "Not Found"}'

    mocker.patch.object(Session, "request", return_value=bad_response)

    iam_user_profile = get_user_command(client, args, "mapper_in", "mapper_out")
    outputs = get_outputs_from_user_profile(iam_user_profile)

    assert outputs.get("action") == IAMActions.GET_USER
    assert outputs.get("success") is False
    assert outputs.get("errorCode") == 500
    assert outputs.get("errorMessage") == "Not Found"


def test_create_user_command__user_already_exists(mocker):
    client = mock_client()
    args = {"user-profile": {"emails": "mock@mock.com"}}

    mocker.patch.object(client, "get_user", return_value=GITHUB_UPDATE_USER_OUTPUT)
    mocker.patch.object(client, "update_user", return_value=GITHUB_UPDATE_USER_OUTPUT)

    iam_user_profile = create_user_command(client, args, "mapper_out", True, True)
    outputs = get_outputs_from_user_profile(iam_user_profile)

    assert outputs.get("action") == IAMActions.UPDATE_USER
    assert outputs.get("success") is True


def test_update_user_command__non_existing_user(mocker):
    client = mock_client()
    args = {"user-profile": {"emails": "mock@mock.com"}}

    mocker.patch.object(client, "get_user", return_value={"totalResults": 0})
    mocker.patch.object(client, "create_user", return_value=GITHUB_CREATE_USER_OUTPUT)

    iam_user_profile = update_user_command(
        client, args, "mapper_out", is_update_enabled=True, is_create_enabled=True, create_if_not_exists=True
    )
    outputs = get_outputs_from_user_profile(iam_user_profile)

    assert outputs.get("action") == IAMActions.CREATE_USER
    assert outputs.get("success") is True
    assert outputs.get("active") is True
    assert outputs.get("id") == "12345"
    assert outputs.get("username") == "TestID@networks.com"


def test_update_user_command__command_is_disabled(mocker):
    client = mock_client()
    args = {"user-profile": {"emails": "mock@mock.com"}}

    mocker.patch.object(client, "get_user", return_value={"totalResults": 0})
    mocker.patch.object(client, "update_user", return_value=GITHUB_UPDATE_USER_OUTPUT)

    user_profile = update_user_command(
        client, args, "mapper_out", is_update_enabled=False, is_create_enabled=False, create_if_not_exists=False
    )
    outputs = get_outputs_from_user_profile(user_profile)

    assert outputs.get("action") == IAMActions.UPDATE_USER
    assert outputs.get("success") is True
    assert outputs.get("skipped") is True
    assert outputs.get("reason") == "Command is disabled."
