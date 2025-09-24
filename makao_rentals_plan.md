# SYSTEM OVERVIEW
## WHAT does the system need to do ?

The system will have two sides the Tenant and the Landlord.

# The landlord
**The system on his side**
- So the landlord needs to view the payments already done by the tenants on his page in a well
made dashboard. He can view all the tenants separately or by property or by all combined.
- He also needs to approve the tenants on his side after they create their accounts so that they can be given the functionalities of the system.
-  He also needs to send emails to the tenants to remind them to pay their rent.

# The Tenant
**The system on his side**
- So the tenant needs to be able to view his payments only. So only his unit.
- He also needs to be able to make payments via the app using mpesa daraja stk push.
- Create an account and log-in to the system.
- Can only be able to use the system once he is approved
- Can reset the password through the system sending a password reset email to their email and they reset their password.
- They also get a confirmation email for signing up telling them that to wait for landlord approval

## HOW will we achieve all these ?
### AUTHENTICATION AND AUTHORIZATION
**How it will work**
So the landlord will first create an account and set up his details like his properties and the names of the property's and the amount of units the property's have. So they will have a notifications tab where they will be notified once a new tenant signs up and they can approve them.

The tenant side will be different so tenants will create their accounts and they will have to select the property they are in so that we can send a request to the landlord to approve them. Once approved they can now use the system. Once they sign up they will be sent an email to wait for landlord authorization and after authorization they will be sent another email for confirmation.

all users will be able to reset their password if they forget so they will get a password reset email with a link they can follow to reset the email. Once the password is changed they get another email saying they have successfully changed their password.

for sign-in we will use JWT authentication. [ so django-simple-jwt ]

so we will have 2 sides of storing data to the database - approved and not approved 
The approved ones can access all the functionality when they login  and the not approved ones will get a page telling them " Waiting for approval"

Redis for cache for faster logging in.

### PAYMENTS
**How it will work**
So we will need to store the transaction data to the system and have to retrieve it in order to show case it to the landlord. Payments will be done in mpesa via the daraja api for stk push and therefore we will need a till number which you can apply via the mpesa developers portal.
So the Tenants should be able to choose and enter how much they want to pay so that we can prompt them to pay that amount and update that data in our database.
We will make payments easily here and store the info to our database.

Redis for cache for faster dashboard data unless the database was updated recently.

#### Contracts


### COMMUNICATION
**How it will work**
The tenant can want to send a message to the landlord and due to project constraints we will not implement TCP for secure end to end messages. We will use only mails for messages which is unrelliable but will work for the mean time.

## Project timeline

Expected to complete it in 1 week - [ BACKEND ONLY ]

Day 1 - Setup authentication and authorization system

Day 2 - Finish up Setup authentication and authorization system

Day 3 -setup Payment System

Day 4 - Finish Up Payment System

Day 5 - Setup Communication System

Day 6 - Finish Up Payment System