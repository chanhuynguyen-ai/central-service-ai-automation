# Canvas App mapping

Use a responsive Canvas App with three views: submit, my requests, and request detail.

## Submit button

```powerfx
If(
    IsBlank(txtTitle.Text) || Len(Trim(txtDescription.Text)) < 15,
    Notify("Add a title and a complete description.", NotificationType.Error),
    Set(
        createdRequest,
        CentralOpsAI.SubmitServiceRequest({
            requester_email: User().Email,
            title: Trim(txtTitle.Text),
            description: Trim(txtDescription.Text),
            category: drpCategory.Selected.Value,
            priority: Lower(drpPriority.Selected.Value),
            source_record_id: Text(GUID())
        })
    );
    Notify("Request " & createdRequest.reference & " submitted.", NotificationType.Success);
    Navigate(scrRequestDetail)
)
```

## Status refresh

```powerfx
Set(currentRequest, CentralOpsAI.GetServiceRequest(createdRequest.reference))
```

Keep AI confidence visible as supporting information. Do not allow the app to turn an AI
recommendation directly into an approval decision.
