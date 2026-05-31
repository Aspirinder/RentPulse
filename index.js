const searchBtn = document.getElementById('search_btn');
const resultCard = document.getElementById('result_card');
const offerTitle = document.getElementById('offer_title');
const price = document.getElementById('price');
const offerImage = document.getElementById('offer_image');
const offerLink = document.getElementById('offer_link');
const prevImg = document.getElementById('prev_img');
const nextImg = document.getElementById('next_img');
const nextOfferBtn = document.getElementById('next_offer_btn');
const saveBtn = document.getElementById('save_btn');
const savedOffersBtn = document.getElementById('show_saved_btn');

let offers = [];
let currentOfferIndex = 0;
let currentImageIndex = 0;

searchBtn.addEventListener('click', async () =>{
    const platforms = [];
    if(document.getElementById('olx').checked) platforms.push('olx.pl');
    if(document.getElementById('otodom').checked) platforms.push('otodom.pl');

    const combined = document.getElementById('combined').checked;

    searchBtn.disabled = true;
    searchBtn.textContent = 'Searching... Please wait...';
    searchBtn.style.opacity = '0.6';
    searchBtn.style.cursor = 'not-allowed';

    const startTimeStamp = performance.now();
    console.log(`🚀 Start search`);

    try{
        const responce = await fetch(`php/fetch_data.php?platforms=${platforms.join(',')}&combined=${combined}`);

        offers = await responce.json();
        
        const endTimeStamp = performance.now();
        const durationMs = endTimeStamp - startTimeStamp;
        const formattedTime = formatDuration(durationMs);

        console.log(`⏱️ Stop search: ${formattedTime}`);

        if(offers.length > 0){
            currentOfferIndex = 0;
            renderOffer();
            resultCard.classList.remove('hidden');
        }else{
            alert('No offers');
            resultCard.classList.add('hidden');
        }
    }catch(error){
        console.error('Error data load:', error);
    }finally{
        searchBtn.disabled = false;
        searchBtn.textContent = "Search";
        searchBtn.style.opacity = '1';
        searchBtn.style.cursor = 'pointer';
    }
});

prevImg.addEventListener('click', (e) => {
    e.stopPropagation();
    const images = offers[currentOfferIndex].Images;
    if (images && images.length > 0) {
        currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
        updateImage();
    }
});

nextImg.addEventListener('click', (e) => {
    e.stopPropagation();
    const images = offers[currentOfferIndex].Images;
    if (images && images.length > 0) {
        currentImageIndex = (currentImageIndex + 1) % images.length;
        updateImage();
    }
});

nextOfferBtn.addEventListener('click', () => {
    if (currentOfferIndex < offers.length - 1) {
        currentOfferIndex++;
        renderOffer();
    } else alert('Last offer!');
});

saveBtn.addEventListener('click', async () => {
    const currentOffer = offers[currentOfferIndex];

    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    try{
        const responce = await fetch('php/save_to_db.php', {
            method: 'POST',
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: JSON.stringify(currentOffer)
        });

        const result = await responce.json();

        if (result.status === 'success') alert("Success save!");
        else if (result.status === 'exists') alert(`${result.message}`);
        else {alert('Error'); console.error(`DB error: ${result.message}`);}

    }catch(error){
        console.error('DB error', error);
        alert('DB error');
    }finally{
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save';
    }
});


function renderOffer(){
    const offer = offers[currentOfferIndex];
    currentImageIndex = 0;

    offerTitle.textContent = `${offer.Title} ${offers.length}` || `No title ${offers.length}`;
    price.textContent = offer.Price;
    
    offerLink.href = offer.Link || '#';

    updateImage();
}

function updateImage() {
    const currentOffer = offers[currentOfferIndex];
    if (currentOffer && currentOffer.Images && currentOffer.Images.length > 0) {
        offerImage.src = currentOffer.Images[currentImageIndex];
    } else {
        offerImage.src = 'https://via.placeholder.com/600x400?text=No+Image';
    }
}

function formatDuration(ms) {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    
    if (minutes > 0) return `${minutes} min. ${seconds} sec.`;
    return `${seconds} sec.`;
}