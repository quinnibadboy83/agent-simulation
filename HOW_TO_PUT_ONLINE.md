# COMPLETE BEGINNER GUIDE  
## How to put Agent Simulation on the internet for FREE  
### So you can open it on your Samsung S25 Ultra

This guide is written for someone who has never done this before.  
Follow every step slowly. Do not skip any step.

We will use two free services:
1. **GitHub** → to store the code
2. **Render** → to run the app online 24/7 for free

Both are free. You do not need a credit card for the free plan.

---------------------------------------

## PART 1 – Create a GitHub account (5 minutes)

1. On your phone, open Chrome.
2. Go to this website:  
   **https://github.com**
3. Tap **Sign up**
4. Enter your email address
5. Create a password
6. Choose a username (example: yourname-agentsim)
7. Verify you are human (solve the puzzle)
8. Choose the free plan when asked
9. You can skip the extra questions

You now have a GitHub account.

---------------------------------------

## PART 2 – Create a new empty repository

1. After logging in, look at the top right. Tap the **+** icon
2. Tap **New repository**
3. Repository name: type exactly → `agent-simulation`
4. Leave it **Public**
5. Do **NOT** tick "Add a README file"
6. Tap the green **Create repository** button

You will now see a page with instructions.  
Leave this page open. We will come back to it.

---------------------------------------

## PART 3 – Upload the code (the slightly harder part)

Because you are on a phone, the easiest way is to use the GitHub website upload feature.

### Step-by-step upload:

1. I will give you a zip file of the whole project.
2. Download that zip file on your phone.
3. Unzip it (most phones can do this by tapping the file).
4. Go back to the GitHub page of your new repository.
5. You will see a link that says **"uploading an existing file"**. Tap it.
6. Now drag or select **all the files and folders** that were inside the zip  
   (the ones named: main.py, requirements.txt, Procfile, core, agents, ui, data, modules, README.md, etc.)
7. Important: Upload the **contents**, not the outer folder itself.
8. Scroll down and tap **Commit changes**

If the phone upload is too annoying, the alternative is:
- Ask a friend with a computer to help upload it once, or
- Wait until you can use a laptop for 10 minutes.

---------------------------------------

## PART 4 – Deploy on Render (the free hosting)

1. On your phone, go to:  
   **https://render.com**
2. Tap **Get Started for Free**
3. Sign up with your **GitHub account** (this is the easiest way)
4. After you are logged in, tap **New +**
5. Tap **Web Service**
6. You will see your GitHub repositories. Find `agent-simulation` and tap **Connect**
7. Fill in the settings exactly like this:

   - **Name**: agent-sim (or anything you like)
   - **Region**: Choose the one closest to you
   - **Branch**: main (or master)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

8. Scroll down to **Instance Type**
9. Choose the **Free** plan
10. Tap **Create Web Service**

Render will now start building your app.  
This usually takes 1–3 minutes the first time.

---------------------------------------

## PART 5 – Open it on your phone

1. When the build finishes, Render will show you a web address.  
   It looks something like:  
   `https://agent-sim-xxxx.onrender.com`
2. Tap that link.
3. Bookmark it or add it to your home screen.
4. You can now use the Agent Simulation from your S25 Ultra.

Note: On the free plan, the app goes to sleep after some time of no use.  
The first time you open it after sleeping, it may take 30–60 seconds to wake up. This is normal for free hosting.

---------------------------------------

## What to do if something goes wrong

- If the build fails, look at the logs on Render. Copy the error and send it to me.
- If the page is blank, wait 1 minute and refresh.
- If you get stuck on any step, just tell me which Part and which number you are on, and I will help you.

---------------------------------------

## After it is online

Once you can open the app on your phone and type commands to the Boss, tell me:

“It is online”

Then we will start adding the next modules (real tools, better intelligence, money-making systems, etc.).

You are doing great. Take it one step at a time.
