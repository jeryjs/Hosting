// ==UserScript==
// @name         JAIN - LMS Attendance Helper
// @namespace    https://greasyfork.org/en/users/781076-jery-js
// @version      1.6
// @description  Simplify the process of taking the attendance in Jain University's LMS.
// @author       Jery
// @license      MIT 
// @match        https://lms.futurense.com/mod/attendance/take.php
// @icon         https://www.nicepng.com/png/detail/270-2701205_jain-heritage-a-cambridge-school-kondapur-jain-university.png
// @grant        none
// ==/UserScript==


/***************************************************************
 * Add a start button to the page and use the
 * button beside it as a reference for the styles.
 ***************************************************************/
let startButton = document.createElement("button");
startButton.innerHTML = "Start taking attendance";
startButton.type = "button";
startButton.className = "btn btn-start"

// Style the start button
startButton.style.position = "inherit";
startButton.style.color = "#fff";
startButton.style.backgroundColor = "#6c757d";
startButton.style.transition = "color 0.15s ease-in-out, background-color 0.15s ease-in-out, border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out";

// Add hover (mouse-in) effects to the start button
startButton.addEventListener("mouseenter", function () {
    startButton.style.backgroundColor = "#5c636a";
    startButton.style.borderColor = "#565e64";
});
// Add hover (mouse-out) effects to the start button
startButton.addEventListener("mouseleave", function () {
    startButton.style.backgroundColor = "6c757d";
    startButton.style.borderColor = "inherit";
});

// Append the start button to the right of the reference element
document.querySelector(".btn.btn-secondary").parentElement.appendChild(startButton);

// Add an event listener to the start button
startButton.addEventListener("click", function () {
    attendance();
});


/***************************************************************
 * Main Function to handle attendance.
 * Shows a prompt for entering students usn number.
 * First marks everyone (who isnt marked yet) as ABSENT
 * and then marks the entered numbers as PRESENT.
 ***************************************************************/
function attendance() {
    // Set all (unmarked) students to ABSENT at start.
    document.querySelector("td.cell.c4 [name='setallstatus-select']").value = "unselected";
    document.querySelector("td.cell.c6 input[name='setallstatuses']").checked = true;

    // Initialize a variable to end loop
    let stop = false;

    // Not using a while loop here because the script works in a single thread,
    // so it wont be able to reflect any changes until the while loop ends.
    let loop = () => {
        if (stop) return;
        // Create a prompt to get usn number of student
        let usn = prompt("Enter the LMS usn number (or enter a non-numeric value to end)");
        // Check wheter the input is a number or else terminate.
        if (isNaN(usn)) {
            stop = true;
        } else {
            // remove whitespaces from usn number
            usn = usn.trim();
            // Initialize the rows and cells
            let rows = document.querySelectorAll("table tr");
            for (let i = 0; i < rows.length; i++) {
                let cells = rows[i].querySelectorAll("td");
                if (cells.length > 0 && cells[3].textContent === "22BTRCA" + serial.toString().padStart(3, '0')) {
                    cells[6].querySelector("input").checked = true;     // Mark the cell (student) for present
                    showToast("Marked S.No." + usn + " as present.")     // Display success message
                    break;
                }
            }
        }
        setTimeout(loop, 0);
    };
    loop();
}


/***************************************************************
 * Display a simple toast message on the top right of the screen
 ***************************************************************/
function showToast(message) {
    var x = document.createElement("div");
    x.innerHTML = message;
    x.style.color = "#000";
    x.style.backgroundColor = "#fdba2f";
    x.style.borderRadius = "10px";
    x.style.padding = "10px";
    x.style.position = "fixed";
    x.style.top = "5px";
    x.style.right = "5px";
    x.style.fontSize = "large";
    x.style.fontWeight = "bold";
    x.style.zIndex = "10000";
    x.style.display = "block";
    x.style.borderColor = "#565e64";
    x.style.transition = "right 2s ease-in-out";
    document.body.appendChild(x);

    setTimeout(function () {
        x.style.right = "-1000px";
    }, 2000);

    setTimeout(function () {
        x.style.display = "none";
        document.body.removeChild(x);
    }, 3000);
}