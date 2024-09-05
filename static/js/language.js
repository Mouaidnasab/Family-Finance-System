document.addEventListener('DOMContentLoaded', () => {
    const langButton = document.getElementById('langButton');
    let currentLang = localStorage.getItem('lang') || 'en';

    // Load the dictionary file
    fetch('../static/dictionary.json')
        .then(response => response.json())
        .then(dictionary => {
            function translateText(text, lang) {
                return dictionary[lang][text] || text;
            }

            function translatePage() {
                const elements = document.querySelectorAll('*');
                elements.forEach(element => {
                    if (element.childNodes.length > 0) {
                        element.childNodes.forEach(node => {
                            if (node.nodeType === Node.TEXT_NODE) {
                                const originalText = node.textContent.trim();
                                if (originalText) {
                                    node.textContent = translateText(originalText, currentLang);
                                }
                            }
                        });
                    }
                });
            }

            function updateDirection() {
                document.body.classList.toggle('rtl', currentLang === 'ar');
                document.body.classList.toggle('ltr', currentLang === 'en');
            }

            langButton.addEventListener('click', () => {
                currentLang = (currentLang === 'en') ? 'ar' : 'en';
                langButton.textContent = (currentLang === 'en') ? 'عربي' : 'English';
                localStorage.setItem('lang', currentLang);
                translatePage();
                updateDirection(); // Update the direction when the language changes
            });

            // Initial translation and direction setup
            translatePage();
            updateDirection();
        });
});
