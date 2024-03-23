# Pardot Visitor Activity Extractor
This script will extract Pardot Visitor Activity, and load it into a Salesforce Custom Object.

## Maintenance

### Changing Connected App Credentials
If it is suspected the Consumer Key and Secret have been compromised, or you simply want to rotate/change them, follow these steps:
1. In Salesforce Setup, go to **App Manager**
1. Locate the Connected app, likely called `Pardot Script Integration`, use the arrow at the left to **View** the App.
1. Click on **Manage Consumer Details**, causing a Pop up to appear asking for MFA
1. Under **Staged Consumer Details**, click the **Generate** button.
1. Click the **Apply** button to put these in place.

Next, we will need to tell Heroku that the values changed.
1. Log in to Heroku, navigate to the App you need to update
1. From the App's **Overview** page, click **Settings**
1. Click **Reveal Config Vars**
1. Using the pencil icon next to the 2 `CONSUMER_` Vars, update the **Value** with what Salesforce generated. Click **Save changes** for each one.
1. (recommended) Test by running the script Ad hoc, steps below.

### Ad hoc script execution
If for whatever reason you want to run the script manually, follow these steps:
1. Log in to Heroku, navigate to the App you want to run
1. From the App's **Overview** page, click **Configure Add-ons**
1. Click **Advanced Scheduler**
1. Near **Triggers**, look at the right for a **More** button-link
1. Click **Execute Trigger**, then **Confirm**
1. Close the Browser tab
1. Back at the Heroku App page, click the **More** button at the top right
1. Click **View logs**.

Once the script is done running, you should see `Process exited with status 0` with a successful run. If you don't, there's some troubleshooting to be done, and hopefully there is an error message above that gives you a hint.

## Set Up
There are a few things that will need to be set up in Salesforce for this solution to work.

1. Create Permission Set
1. Create User
1. Create Connected App
1. Create Heroku App
1. Configure Heroku App

### Create Permission Set
1. Create a new Permission Set. Give it a name you will remember, recommended: `Pardot Script Access`
1. Grant the System Permission `Set Audit Fields upon Record Creation`. If you don't see it, you will need to enable it in Setup > User Interface > User Interface
1. Grant Read & Create access to `Pardot_Activity__c`, and edit access to all fields.
1. Grant Read object access to `Contact`, `Lead`, `Campaign` objects. No need to select any fields.

### Create User
Create a new Salesforce User which will need access to Pardot
1. (recommended) First Name: `Pardot Script`
1. (recommended) Last Name: `Integration`
1. Alias: allow autofill
1. Email: not really needed, though recommend it's an email you can monitor
1. Username: whatever you like
1. Nickname: whatever you like
1. User License: `Salesforce Integration`
1. Profile: `Salesforce API Only Systems Integrations` (if you've cloned your own profiles from this, pick the right one)
1. Active: `checked`

There is no need to set the password or remember what it is.

Save the new User, then:
1. Add the Permission Set License: `Salesforce API Integration`. This allows the User to make API calls, and (if granted by Permissions) access to Salesforce Objects
1. Add the Permission Set you created above. This grants access to the 4 Salesforce Objects.

### Create Connected App
In Salesforce Setup, go to App Manager and create a New Connected App.
1. (recommended) Connected App Name: `Pardot Script Integration`
1. API Name: allow autofill
1. Contact Email: who should an Admin email next year when looking at this with no clue?
1. (recommended) Description: `Allows a Python Script to make API calls to Pardot and Salesforce to automate data tasks.`
1. Enable OAuth Settings: `checked`
1. Callback URL: `https://doesntmatter.com` We don't need this, but it is forced as a required field.
1. Selected OAuth Scopes:
   1. Manage Pardot services (pardot_api) - This allows the script to get Visitor Activity records from Pardot
   1. Manage user data via APIs (api) - This allows the script to load `Pardot_Activity__c` with data
   1. Perform requests at any time (refresh_token, offline_access) - This allows the script to run without human intervention
1. Require Proof Key for Code Exchange (PKCE) Extension for Supported Authorization Flows: `unchecked`
1. Enable Client Credentials Flow: `checked`

Save this new Connected App, then retrieve the Consumer Key and Secret, which will be used later. Annoyingly, this currently pops up a new window requiring MFA before presenting the 2 values.

1. Back at the Connected App, click the **Manage** button at the top. 
1. Next, click the **Edit Policies** button, also at the top.
1. Client Credentials Flow -> Run As: Select the User you created above

Click **Save**

### Create Heroku App

#### First time Heroku User
Sign up for Heroku. The sign up process is a bit weird where it asks you to choose the kind of plan you want, though it's not actually specified until Apps are created.

Once Signed In, add a Payment Method.

#### Creating the App
From the Heroku Dashboard https://dashboard.heroku.com/apps, Click the **New** button
1. Select **Create new app**
1. (recommended) App name: `customername-python-script`. If you plan on having more than 1 script run for a customer, you might want to use a more descriptive name.
Click the **Create app** button. After it is created, you will arrive on the **Deploy** screen, but we'll come back to this later.

#### Adding Configuration Values
Configuration values are specific to this "instance" of the script, running for just this customer.

From the App Overview or Deploy page, click on the **Settings** tab.
1. Click the **Reveal Config Vars** button
1. Add the following:
   1. `BUSINESS_UNIT_ID`: this should come from Salesforce Setup > Business Units. Should start with `OUv`
   1. `CONSUMER_KEY`: this came from the Connected App popup screen
   1. `CONSUMER_SECRET`: this came from the Connected App popup screen
   1. `DAYS_AGO`: Used for the very first run, decide how far back you might want to populate Salesforce records
   1. `LOGIN_URL`: Should be in the format of `https://mydomain.my.salesforce.com`, similar to `https://coolcompany.my.salesforce.com`


#### Deploying the App from GitHub
From the App Overview page, click on the **Deploy** tab.
1. Deployment method: **GitHub**
1. Search for the repository: `pardot-activity-extract`, click the **Connect** button
1. Click the **Enable Automatic Deploys**, which will cause the app to update if the source code is changed (like for a bug fix).
1. Click the **Deploy Branch** button. This will "build" the app and get it ready to be run.
1. The build log will appear and show you its work. Once done, it will disappear and you should see **Your app was successfully deployed.**  Don't bother clicking View, as our app doesn't have anything to look at. (Usually Heroku Apps are web apps)

### Configure Scheduled Job
These steps largely follow a cool blog post: https://medium.com/analytics-vidhya/schedule-a-python-script-on-heroku-a978b2f91ca8

1. From the Heroku App Overview or Deploy page, click the Configure Add-ons link
1. Find the `Advanced Scheduler` addon, and add it.
1. Click the **Advanced Scheduler** link (opens in a new tab)
1. Click the **Generate API Token** button
1. Click the **Create Trigger** button
1. (recommended) Name: Daily Process
1. Command: `python script.py`
1. State: `Active`
1. Type: `Recurring`
1. Schedule: `Schedule Helper`
1. Unit of Time: `Day`
1. Select a time, recommend off-hours.
Click **Save**