Create IAM Identity Providers in both accounts:

Go to IAM → Identity providers → Add provider
Provider type: OpenID Connect
Provider URL: https://token.actions.githubusercontent.com
Audience: sts.amazonaws.com 


{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}



~ $ aws quicksight describe-asset-bundle-import-job --aws-account-id 565393024852 --asset-bundle-import-job-id test
{
    "Status": 200,
    "JobStatus": "FAILED_ROLLBACK_COMPLETED",
    "Errors": [
        {
            "Arn": "arn:aws:quicksight:us-east-1:565393024852:dashboard/69af90bd-66e9-45ad-a76e-8bcc5b9e3566",
            "Type": "com.amazonaws.services.quicksight.model.DashboardError",
            "Message": "[{Type: COLUMN_NOT_FOUND,Message: Field id 'fcfcbd11-7b07-47d6-b9db-12c162d58ac6.2.1742367491060' in DataBarsOptions not found in field wells,ViolatedEntities: [{Path: sheet/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_666889db-86b3-4433-8acb-61f2156ef9a6/visual/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_3b260a73-fbfb-4a86-8a9a-e5b1399d442b/field/fcfcbd11-7b07-47d6-b9db-12c162d58ac6.2.1742367491060}]}, {Type: COLUMN_NOT_FOUND,Message: Field id 'fcfcbd11-7b07-47d6-b9db-12c162d58ac6.1.1742367153588' in DataBarsOptions not found in field wells,ViolatedEntities: [{Path: sheet/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_666889db-86b3-4433-8acb-61f2156ef9a6/visual/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_d3626498-ca93-4f49-b537-a6721df8d5e5/field/fcfcbd11-7b07-47d6-b9db-12c162d58ac6.1.1742367153588}]}, {Type: COLUMN_NOT_FOUND,Message: Field id 'e072b660-3cd5-4551-98f9-32c90d35e032.1.1741681943329' in DataBarsOptions not found in field wells,ViolatedEntities: [{Path: sheet/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_3342a8a3-cebc-4489-ab1a-63aa01fab1eb/visual/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_ce15f5de-b79d-4ff9-8984-a0561853272a/field/e072b660-3cd5-4551-98f9-32c90d35e032.1.1741681943329}]}, {Type: COLUMN_NOT_FOUND,Message: Field id 'e072b660-3cd5-4551-98f9-32c90d35e032.1.1741682144173' in DataBarsOptions not found in field wells,ViolatedEntities: [{Path: sheet/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_3342a8a3-cebc-4489-ab1a-63aa01fab1eb/visual/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_9ac31383-ab46-4109-929a-c24cc5c134e1/field/e072b660-3cd5-4551-98f9-32c90d35e032.1.1741682144173}]}, {Type: COLUMN_NOT_FOUND,Message: Field id 'e072b660-3cd5-4551-98f9-32c90d35e032.2.1741682638188' in DataBarsOptions not found in field wells,ViolatedEntities: [{Path: sheet/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_3342a8a3-cebc-4489-ab1a-63aa01fab1eb/visual/69af90bd-66e9-45ad-a76e-8bcc5b9e3566_bf407c54-0d23-47d0-b60b-f41663019785/field/e072b660-3cd5-4551-98f9-32c90d35e032.2.1741682638188}]}]"
        }





        Big query-based datasets are not supported through AAC/AAB bundles today. The support is expected to be released later in the year. You would need to start working on creating the datasets manually in higher environments before your production rollouts.  You will also need to use AAC APIs to do the promotion.
