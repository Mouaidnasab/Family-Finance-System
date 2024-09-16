document.addEventListener("DOMContentLoaded", function() {
    const modal = document.getElementById("uploadModal");
    const btn = document.getElementById("uploadBtn");
    const span = document.getElementsByClassName("close")[0];

    btn.onclick = function() {
        modal.style.display = "block";
    }

    span.onclick = function() {
        modal.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    let isResizing = false;
    let currentTh = null;
    let startOffset = 0;

    document.querySelectorAll('thead th').forEach(th => {
        const handle = document.createElement('div');
        handle.style.width = '5px';
        handle.style.height = '100%';
        handle.style.position = 'absolute';
        handle.style.right = '0';
        handle.style.top = '0';
        handle.style.cursor = 'col-resize';
        handle.addEventListener('mousedown', (e) => {
            isResizing = true;
            currentTh = th;
            startOffset = th.offsetWidth - e.pageX;
            th.classList.add('resizing');
        });
        th.appendChild(handle);
    });

    document.addEventListener('mousemove', (e) => {
        if (isResizing) {
            currentTh.style.width = startOffset + e.pageX + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            currentTh.classList.remove('resizing');
            currentTh = null;
        }
    });

});

let currentIndex = 0;
let unmatchedDescriptions = [];

function showNewDetailsPopup(descriptions) {
    unmatchedDescriptions = descriptions;
    currentIndex = 0;
    updatePopupContent();
    document.getElementById("newDetailsPopup").style.display = "block";
}

function updatePopupContent() {
    const popupContent = document.getElementById("newDetailsContent");
    popupContent.innerHTML = '';

    if (unmatchedDescriptions.length > 0) {
        const description = unmatchedDescriptions[currentIndex];
        const div = document.createElement('div');
        div.classList.add('details-form');
        div.innerHTML = `
            <h3>${description}</h3>
            <label>Unique_Description: <input type="text" data-description="${description}" name="unique_description"></label>
            <label>Segment: <input type="text" data-description="${description}" name="segment"></label>
            <label>Type: <input type="text" data-description="${description}" name="type"></label>
            <label>Sub Type: <input type="text" data-description="${description}" name="sub_type"></label>
            <label>Category: <input type="text" data-description="${description}" name="category"></label>
            <label>Sub Category: <input type="text" data-description="${description}" name="sub_category"></label>
            <label>Location Used: <input type="text" data-description="${description}" name="country_used"></label>
            <button onclick="submitNewDetail('${description}')">Submit</button>
        `;
        popupContent.appendChild(div);

        document.getElementById("navigationButtons").style.display = currentIndex === unmatchedDescriptions.length - 1 ? "none" : "block";
        document.getElementById("confirmButton").style.display = currentIndex === unmatchedDescriptions.length - 1 ? "block" : "none";
    }
}

function prevDetail() {
    if (currentIndex > 0) {
        currentIndex--;
        updatePopupContent();
    }
}

function nextDetail() {
    if (currentIndex < unmatchedDescriptions.length - 1) {
        currentIndex++;
        updatePopupContent();
    }
}


function clearTable() {
    fetch('/clear_content', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(result => {
        showMessage(result.message, result.status);
        if (result.status === 'success') {
            setTimeout(() => location.reload(), 1000);
        }
    })
    .catch(error => {
        showMessage(error, 'error');
    });
}

function submitNewDetail(description) {
    const inputs = document.querySelectorAll(`.details-form input[data-description="${description}"]`);
    const data = {
        transaction_description: description
    };

    inputs.forEach(input => {
        data[input.name] = input.value;
    });

    fetch('/add_transaction_detail', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        showMessage(result.message, result.status);
        if (result.status === 'success') {
            if (currentIndex === unmatchedDescriptions.length - 1) {
                document.getElementById("newDetailsPopup").style.display = "none";
            } else {
                nextDetail();
            }
        }
    })
    .catch(error => showMessage(error, 'error'));
}

function callUpdateTransactionsTemp() {
    fetch("/UpdateTransactionsTemp")
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                showMessage('Auto-fill completed successfully!', 'message');
                setTimeout(() => location.reload(), 1000);  // Refresh the page after 1 second
            } else {
                showMessage(result.message, 'error');

            }
        })
        
        .catch(error => showMessage(error, 'error'));

        setTimeout(() => location.reload(), 1000);  // Refresh the page after 1 second

}



function showMessage(message, type) {
    if (message) {
        const messageBoxContainer = document.getElementById('messageBoxContainer');
        const newMessageBox = document.createElement('div');
        newMessageBox.textContent = message;
        newMessageBox.classList.add(type === 'error' ? 'error' : 'message');
        messageBoxContainer.appendChild(newMessageBox);
        setTimeout(() => {
            newMessageBox.remove();
        }, 5000);  // Display for 5 seconds
    }
}

function showConfirmPopup() {
    const confirmList = document.getElementById("confirmDescriptions");
    confirmList.innerHTML = '';

    unmatchedDescriptions.forEach(description => {
        const inputs = document.querySelectorAll(`.details-form input[data-description="${description}"]`);
        let filled = true;

        inputs.forEach(input => {
            if (input.value === '') {
                filled = false;
            }
        });

        if (filled) {
            const li = document.createElement('li');
            li.textContent = description;
            confirmList.appendChild(li);
        }
    });

    document.getElementById("confirmationModal").style.display = "block";
}

function confirmSubmission() {
    const confirmList = document.getElementById("confirmDescriptions").children;

    Array.from(confirmList).forEach(item => {
        const description = item.textContent;
        submitNewDetail(description);
    });

    document.getElementById("confirmationModal").style.display = "none";
    document.getElementById("newDetailsPopup").style.display = "none";
}

function cancelSubmission() {
    document.getElementById("confirmationModal").style.display = "none";
}

function closeNewDetailsPopup() {
    document.getElementById("newDetailsPopup").style.display = "none";
}

function closeConfirmationModal() {
    document.getElementById("confirmationModal").style.display = "none";
}


function addRow() {
    const rowCount = parseInt(document.getElementById('addrows').value, 10) || 1;
    if (rowCount < 1) return;

    fetch('/add_rows', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ rows: rowCount })
    })
    .then(response => response.json())
    .then(result => {
        showMessage(result.message, result.status);
        if (result.status === 'success') {
            setTimeout(() => location.reload(), 500);
        }
    })
    .catch(error => {
        showMessage(error, 'error');
    });

    document.getElementById("uploadModal").style.display = "none";
}

function checkAll() {
    $.post('/check_all', function(response) {
        if (response.status === 'success') {
            showMessage(response.message, 'message');
            location.reload();  // Reload the page to reflect changes
        } else {
            showMessage(response.message, 'error');
        }
    });
}

// Function to uncheck all checkboxes
function uncheckAll() {
    $.post('/uncheck_all', function(response) {
        if (response.status === 'success') {
            showMessage(response.message, 'message');
            location.reload();  // Reload the page to reflect changes
        } else {
            showMessage(response.message, 'error');
        }
    });
}function checkAll() {
            $.post('/check_all', function(response) {
                if (response.status === 'success') {
                    showMessage(response.message, 'message');
                    location.reload();  // Reload the page to reflect changes
                } else {
                    showMessage(response.message, 'error');
                }
            });
        }

        // Function to uncheck all checkboxes
        function uncheckAll() {
            $.post('/uncheck_all', function(response) {
                if (response.status === 'success') {
                    showMessage(response.message, 'message');
                    location.reload();  // Reload the page to reflect changes
                } else {
                    showMessage(response.message, 'error');
                }
            });
        }