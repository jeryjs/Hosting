echo off
echo adding "%1"
git add "%1"
echo Now enter the summary for this commit
git commit
echo commiting...
git push
echo push success!!
echo on
timeout /t 10
