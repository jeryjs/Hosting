echo off
git add "%1"
echo Now enter the summary for this commit
git commit
git push
echo success!!
echo Exiting git
timeout /t 10