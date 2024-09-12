// Declare global functions
function translateText(text, lang, dictionary) {
    return dictionary[lang][text] || text;
}

function translatePage(dictionary, currentLang) { 
    console.log(/'hhhh'/)
    const elements = document.querySelectorAll('*');
    elements.forEach(element => {
        if (element.childNodes.length > 0) {
            element.childNodes.forEach(node => {
                if (node.nodeType === Node.TEXT_NODE) {
                    const originalText = node.textContent.trim();
                    if (originalText) {
                        node.textContent = translateText(originalText, currentLang, dictionary);
                    }
                }
            });
        }
    });
}

function updateDirection(currentLang) {
    document.body.classList.toggle('rtl', currentLang === 'ar');
    document.body.classList.toggle('ltr', currentLang === 'en');
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('language.js loaded')
    const langButton = document.getElementById('langButton');
    let currentLang = localStorage.getItem('lang') || 'en';
    let dictionary = {};

    // Load the dictionary file
    fetch('../static/dictionary.json')
        .then(response => response.json())
        .then(dict => {
            dictionary = dict;

            
            langButton.addEventListener('click', () => {
                currentLang = (currentLang === 'en') ? 'ar' : 'en';
                langButton.textContent = (currentLang === 'en') ? 'عربي' : 'English';
                localStorage.setItem('lang', currentLang);
                translatePage(dictionary, currentLang);
                updateDirection(currentLang); // Update the direction when the language changes
            });

            // Initial translation and direction setup
            translatePage(dictionary, currentLang);
            updateDirection(currentLang);

            // Periodic updates
            setInterval(() => {
                translatePage(dictionary, currentLang);
                updateDirection(currentLang);
            }, 500); // Update every 5 seconds (adjust as needed)
        });
});
