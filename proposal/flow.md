flowchart TD
    ExistingUser["Existing User"] -- Login --> Login["Authenticate with TOTP/username"] --> Filter["Filter MBIDs based on user input"]
    NewUser["New User"] -- Create Account --> DataImport["Import data from APIs"] -- Login --> Login
    Filter -- Generate Listening Report --> DisplayReport["Display ASCII report"]
    Filter -- Search Artist/Album/Track --> Result["Print result list"]
    Filter -- Reccomend Artist/Album/Track --> Sort["Find the n least frecent MBIDs"] --> Result
