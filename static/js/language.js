 // Declare global variables
 let currentLang = localStorage.getItem('lang') || 'en'; // Set default language
 let dictionary = {}; // Initialize an empty dictionary
 
 // Function to translate text based on the current language and dictionary
 function translateText(text, lang, dictionary) {
     return dictionary[lang] && dictionary[lang][text] || text; // Return translated text if available, else original text
 }
 
 // Function to translate all elements with the "data-translate" attribute
 function translatePage(dictionary, currentLang) {
     const elements = document.querySelectorAll('[data-translate]');
     elements.forEach(element => {
         const key = element.getAttribute('data-translate');
         if (key && dictionary[currentLang] && dictionary[currentLang][key]) {
             element.textContent = dictionary[currentLang][key];
         }
     });

         // Translate input placeholders
     const placeholderElements = document.querySelectorAll('[data-translate-placeholder]');
     placeholderElements.forEach(element => {
         const key = element.getAttribute('data-translate-placeholder');
         if (key && dictionary[currentLang] && dictionary[currentLang][key]) {
             element.placeholder = dictionary[currentLang][key];
         }
     });

     // Translate input values (like submit buttons)
     const valueElements = document.querySelectorAll('[data-translate-value]');
     valueElements.forEach(element => {
         const key = element.getAttribute('data-translate-value');
         if (key && dictionary[currentLang] && dictionary[currentLang][key]) {
             element.value = dictionary[currentLang][key];
         }
     });
     }
 
 // Function to update the page direction (RTL or LTR) based on the current language
 function updateDirection(currentLang) {
     document.body.classList.toggle('rtl', currentLang === 'ar');
     document.body.classList.toggle('ltr', currentLang === 'en');
     updateLanguageAttribute(currentLang);
 }
 
 // Function to update the `lang` attribute of the HTML tag
 function updateLanguageAttribute(currentLang) {
     document.documentElement.lang = currentLang;
 }
 
 // Function to handle the click event of the language button
 function handleLanguageChange() {
     currentLang = (currentLang === 'en') ? 'ar' : 'en'; // Toggle language
     localStorage.setItem('lang', currentLang); // Save the selected language to localStorage

     location.reload();
 
     // Update the button text based on the selected language
     const langButton = document.getElementById('langButton');
     langButton.textContent = (currentLang === 'en') ? 'عربي' : 'English';
 
     // Perform the translation and update direction
     translatePage(dictionary, currentLang);
     updateDirection(currentLang);

 }
 
 // Load the translation dictionary file
 function loadDictionary() {
     return fetch('/static/dictionary.json')
         .then(response => response.json())
         .then(dict => {
             dictionary = dict; // Assign the loaded dictionary to the global variable
             console.log('Dictionary loaded:', dictionary);
             return dictionary;
         })
         .catch(error => {
             console.error('Error loading translation dictionary:', error);
         });
 }
 
 // Initialize the translation and event listeners
 document.addEventListener('DOMContentLoaded', () => {
     console.log('language.js loaded');
     const langButton = document.getElementById('langButton');
 
     // Load the dictionary and apply the initial translation
     loadDictionary().then(() => {
         // Set up the language button click event
         langButton.addEventListener('click', handleLanguageChange);
 
         // Initial translation and direction setup
         translatePage(dictionary, currentLang);
         updateDirection(currentLang);
         langButton.textContent = (currentLang === 'en') ? 'عربي' : 'English';

     });
 });
 
