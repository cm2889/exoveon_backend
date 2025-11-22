from django.test import TestCase

# Create your tests here.



""" 

Google Calendar Event Creation Examples



{ 
    
    "summary": "Demo Event",
    "description": "Testing creation",
    "start_datetime": "2025-11-20T10:00:00Z", 
    "end_datetime": "2025-11-20T11:00:00Z", 
    "timezone": "UTC", 
    "location": "Virtual", 
    "attendees": [], 
    "reminders": true
     
 }

 
 {

    "full_name": "Asif Faislal",

    "email": "asif1920001@gmail.com",

    "phone_number": "01516373037",

    "summary": "Budget Review and Approvals",

    "description": "Final review of department budget proposals for Q4 2025. Please bring hard copies of your P&L summaries. Meeting is mandatory.",

    "location": "Paris Office - Main Boardroom",

    "attendees": "", 

    "timezone": "Europe/Paris",

    "date": "2025-11-20",

    "start_datetime": "2025-11-21T14:00:00",

    "end_datetime": "2025-11-21T16:00:00",

    "reminders": true

}

{  
    "summary": "Client Call", 
    "description": "Discuss requirements", 
    "start_datetime": "2025-11-22T15:00:00Z", 
    "end_datetime": "2025-11-22T16:00:00Z", 
    "timezone": "UTC",, 
    "attendees": ["f.asif.official@example.com"], 
    "send_notifications": true, 
    "reminders": true 
}



"""