import demistomock as demisto  # noqa: F401
from CommonServerPython import *  # noqa: F401

try:
    # Delete indicators generated by the OnboardingIntegration
    delete_indicators_cmd_args = {"query": "incident.sourceBrand:OnboardingIntegration", "doNotWhitelist": "true"}
    command_result = demisto.executeCommand("deleteIndicators", delete_indicators_cmd_args)
    if isError(command_result[0]):
        raise Exception(command_result[0])
    demisto.results("Indicators added by incidents generated by the OnboardingIntegration have been deleted.")

    # Close incidents of type Phishing that were created by OnboardingIntegration
    get_incidents_cmd_args = {"query": "type:Phishing and sourceBrand:OnboardingIntegration and -status:Closed"}
    res_get_incidents = demisto.executeCommand("getIncidents", get_incidents_cmd_args)

    incidents = res_get_incidents[0].get("Contents", {}).get("data")
    res = []
    if incidents:
        for incident in incidents:
            incident_id = incident.get("id")
            incident_name = incident.get("name")
            res.append({"Incident ID": incident_id, "Incident Name": incident_name})
            close_investigation_cmd_args = {
                "id": incident_id,
                "closeNotes": "Closing all incidents of type PhishingDemo. (Cleanup)",
            }
            demisto.executeCommand("closeInvestigation", close_investigation_cmd_args)
    headers = ["Incident ID", "Incident Name"]
    title = f"Total Incidents Closed: {len(res)}"
    human_readable = tableToMarkdown(title, res, headers=headers, removeNull=True)
    demisto.results(
        {
            "Type": entryTypes["note"],
            "Contents": res,
            "ContentsFormat": formats["json"],
            "ReadableContentsFormat": formats["markdown"],
            "HumanReadable": human_readable,
        }
    )
except Exception as e:
    demisto.results(
        {
            "Type": entryTypes["error"],
            "ContentsFormat": formats["text"],
            "Contents": "A problem occurred while trying to execute this script. Exception info:\n" + str(e),
        }
    )
