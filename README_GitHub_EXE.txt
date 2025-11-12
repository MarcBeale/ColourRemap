README (No-code Windows EXE via GitHub)

You will upload these files to GitHub and get a Windows EXE as a build artifact.

Steps:
1) Create a new GitHub repo (public or private).
2) Upload:
   - app/MonoColourLUT_GUI.py
   - .github/workflows/build.yml
   - requirements.txt
   - sample_lut.csv (optional; replace with your own later)
3) Go to the Actions tab, open the running workflow, download the artifact MonoColourLUT-win64.zip when it completes.
4) Extract and run MonoColourLUT.exe.
