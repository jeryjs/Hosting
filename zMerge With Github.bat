echo off
echo adding "%1"
echo on
git add "%1"
echo off
echo Now enter the summary for this commit
echo on
git commit
git push
echo off
echo push success!!
echo on
timeout /t 10
