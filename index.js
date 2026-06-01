/* ==========================================================================
   1. DOM ELEMENTS SELECTION
   ========================================================================== */
const searchBtn = document.getElementById('search_btn');
const resultCard = document.getElementById('result_card');
const offerTitle = document.getElementById('offer_title');
const price = document.getElementById('price');
const offerImage = document.getElementById('offer_image');
const offerLink = document.getElementById('offer_link');
const prevImg = document.getElementById('prev_img');
const nextImg = document.getElementById('next_img');
const nextOfferBtn = document.getElementById('next_offer_btn');
const prevOfferBtn = document.getElementById('prev_offer_btn');
const saveBtn = document.getElementById('save_btn');
const savedOffersBtn = document.getElementById('show_saved_btn');
const bottomPanel = document.getElementById('bottom_panel');

/* ==========================================================================
   2. GLOBAL STATE VARIABLES
   ========================================================================== */
let offers = [];               // Holds the array of apartment objects fetched from API
let currentOfferIndex = 0;     // Pointer to the currently viewed offer card
let currentImageIndex = 0;     // Pointer to the active image inside the active card's gallery

/* ==========================================================================
   3. DYNAMIC UI INITIALIZATION
   ========================================================================== */
// Generate container for saved records and append it to the bottom panel
const savedListContainer = document.createElement('div');
savedListContainer.id = 'saved_offers_list';
savedListContainer.style.display = 'none';
bottomPanel.appendChild(savedListContainer);

/* ==========================================================================
   4. EVENT LISTENERS & API REQUESTS
   ========================================================================== */

/**
 * Event Listener for the main search action button.
 * Triggers the AWS API multi-page fetch process via local PHP proxy.
 */
searchBtn.addEventListener('click', async () => {
    const platforms = [];
    if(document.getElementById('olx').checked) platforms.push('olx.pl');
    if(document.getElementById('otodom').checked) platforms.push('otodom.pl');

    const combined = document.getElementById('combined').checked;

    // Visual feedback: Disable button and show loading state
    searchBtn.disabled = true;
    searchBtn.textContent = 'Searching... Please wait...';
    searchBtn.style.opacity = '0.6';
    searchBtn.style.cursor = 'not-allowed';

    // Start tracking API performance duration
    const startTimeStamp = performance.now();
    console.log(`🚀 Start search`);

    try {
        // Request the aggregated records from the PHP proxy script
        const response = await fetch(`php/fetch_data.php?platforms=${platforms.join(',')}&combined=${combined}`);
        offers = await response.json();
        
        // Compute and print query duration metrics
        const endTimeStamp = performance.now();
        const durationMs = endTimeStamp - startTimeStamp;
        const formattedTime = formatDuration(durationMs);
        console.log(`⏱️ Stop search: ${formattedTime}`);

        // Handle the incoming dataset
        if(offers.length > 0) {
            currentOfferIndex = 0;
            renderOffer();
            resultCard.classList.remove('hidden');
        } else {
            alert('No offers found for selected criteria.');
            resultCard.classList.add('hidden');
        }
    } catch(error) {
        console.error('Error loading offer data:', error);
        alert('An error occurred while fetching data from the server.');
    } finally {
        // Restore standard button state regardless of success or failure
        searchBtn.disabled = false;
        searchBtn.textContent = "Search";
        searchBtn.style.opacity = '1';
        searchBtn.style.cursor = 'pointer';
    }
});

/**
 * Image gallery navigation: Move to the previous image.
 */
prevImg.addEventListener('click', (e) => {
    e.stopPropagation(); // Prevent event bubbling to parent containers
    const images = offers[currentOfferIndex].Images;
    if (images && images.length > 0) {
        // Cyclic decrement calculation using array length modulo
        currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
        updateImage();
    }
});

/**
 * Image gallery navigation: Move to the next image.
 */
nextImg.addEventListener('click', (e) => {
    e.stopPropagation(); // Prevent event bubbling to parent containers
    const images = offers[currentOfferIndex].Images;
    if (images && images.length > 0) {
        // Cyclic increment calculation using modulo operator
        currentImageIndex = (currentImageIndex + 1) % images.length;
        updateImage();
    }
});

/**
 * Offer card navigation: Advance to the next offer in the array.
 */
nextOfferBtn.addEventListener('click', () => {
    if (currentOfferIndex < offers.length - 1) {
        currentOfferIndex++;
        renderOffer();
    } else {
        alert('You are viewing the last available offer!');
    }
});

/**
 * Offer card navigation: Go back to the previous offer in the array.
 */
prevOfferBtn.addEventListener('click', () => {
    if (currentOfferIndex > 0) {
        currentOfferIndex--;
        renderOffer();
    } else {
        alert('You are viewing the first offer!');
    }
});

/**
 * Action button: Saves the active offer to the MySQL local instance.
 */
saveBtn.addEventListener('click', async () => {
    const currentOffer = offers[currentOfferIndex];

    // Secure the save operation UI
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try {
        const response = await fetch('php/save_to_db.php', {
            method: 'POST',
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: JSON.stringify(currentOffer)
        });

        const result = await response.json();

        // Evaluate backend processing status response
        if (result.status === 'success') {
            alert("Offer saved successfully!");
        } else if (result.status === 'exists') {
            alert(`${result.message}`); // Display custom duplicate database entry note
        } else {
            alert('Could not save offer.');
            console.error(`DB error: ${result.message}`);
        }
    } catch(error) {
        console.error('Database connection error:', error);
        alert('DB script connection error.');
    } finally {
        // Re-enable save button interface
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save';
    }
});

/**
 * Action button: Toggle and pull recorded bookmarks from the relational schema.
 */
savedOffersBtn.addEventListener('click', async () => {
    // Dropdown view toggle condition
    if (savedListContainer.style.display === 'block') {
        savedListContainer.style.display = 'none';
        savedOffersBtn.textContent = 'Show saved offers';
        return;
    }

    try {
        savedOffersBtn.textContent = 'Loading...';
            
        const response = await fetch('php/get_saved.php');
        if (!response.ok) throw new Error('Failed to retrieve list.');
            
        const savedOffers = await response.json();
        savedListContainer.innerHTML = ''; // Wipe past layout calculations

        // Render records map array or empty table feedback banner
        if (savedOffers.length === 0) {
            savedListContainer.innerHTML = '<p class="no_saved">No saved offers in DB.</p>';
        } else {
            savedOffers.forEach(offer => {
                const row = document.createElement('div');
                row.className = 'saved_offer_row';
                
                // Maps standard indexed row parameters safely to strict HTML nodes
                row.innerHTML = `
                    <span class="saved_title" title="${offer.title}">${offer.title}</span>
                    <span class="saved_price">${offer.price}</span>
                    <a class="saved_link" href="${offer.link}" target="_blank">Link →</a>
                `;
                    
                savedListContainer.appendChild(row);
            });
        }

        // Show the panel container
        savedListContainer.style.display = 'block';
        savedOffersBtn.textContent = 'Hide saved';

    } catch (error) {
        console.error(error);
        alert('Database error: ' + error.message);
        savedOffersBtn.textContent = 'Show saved offers';
    }
});

/* ==========================================================================
   5. HELPER CORE RENDER FUNCTIONS
   ========================================================================== */

/**
 * Updates the card views with metadata related to the active dataset pointer.
 */
function renderOffer() {
    const offer = offers[currentOfferIndex];
    currentImageIndex = 0; // Reset image viewer tracker for every newly pulled offer card

    offerTitle.textContent = `${offer.Title} (${currentOfferIndex + 1}/${offers.length})` || `No title context (${currentOfferIndex + 1}/${offers.length})`;
    price.textContent = offer.Price;
    offerLink.href = offer.Link || '#';

    updateImage();
}

/**
 * Evaluates conditions and sets the gallery view element source link.
 */
function updateImage() {
    const currentOffer = offers[currentOfferIndex];
    if (currentOffer && currentOffer.Images && currentOffer.Images.length > 0) {
        offerImage.src = currentOffer.Images[currentImageIndex];
    } else {
        // Fallback placeholder image when an offer contains an empty gallery link array
        offerImage.src = 'https://via.placeholder.com/600x400?text=No+Image+Available';
    }
}

/**
 * Parses raw Performance API millisecond intervals into clear text statements.
 */
function formatDuration(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    
    if (minutes > 0) return `${minutes} min. ${seconds} sec.`;
    return `${seconds} sec.`;
}