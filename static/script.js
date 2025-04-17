// static/script.js
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("prompt-form");
    const submitBtn = document.getElementById("submit-btn");
    const progressContainer = document.getElementById("progress-container");
    const progressBar = document.getElementById("progress-bar");
    const progressPercentage = document.getElementById("progress-percentage");
    const resultsContainer = document.getElementById("character-results");
    const errorMessage = document.getElementById("error-message");
    let progressInterval = null;
  
    const simulateProgress = () => {
        let progress = 0;
        progressBar.value = 0;
        progressPercentage.textContent = "0%";
        progressContainer.style.display = "block";
        errorMessage.innerText = ""; // Clear previous errors
  
        if (progressInterval) {
            clearInterval(progressInterval);
        }
  
        progressInterval = setInterval(() => {
            progress += 2;
            if (progress <= 95) {
                progressBar.value = progress;
                progressPercentage.textContent = `${progress}%`;
            } else {
                clearInterval(progressInterval);
                progressInterval = null;
            }
        }, 150);
    };
  
    const finalizeProgress = (isSuccess = true) => {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
        if (isSuccess) {
            progressBar.value = 100;
            progressPercentage.textContent = "100%";
        } else {
             // Keep progress where it stopped on failure, or reset? Reset looks cleaner.
             progressBar.value = 0;
             progressPercentage.textContent = `0%`;
        }
        setTimeout(() => {
            progressContainer.style.display = "none";
            submitBtn.disabled = false;
        }, isSuccess ? 500 : 100); // Hide faster on error
    };
  
    form.addEventListener("submit", (event) => {
        event.preventDefault();
  
        errorMessage.innerText = "";
        resultsContainer.innerHTML = "";
        resultsContainer.style.display = "none";
        submitBtn.disabled = true;
  
        simulateProgress();
  
        const userInput = document.getElementById("prompt").value;
        if (!userInput.trim()) {
            errorMessage.innerText = "Please enter some personality traits.";
            finalizeProgress(false);
            return;
        }
  
        fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ prompt: userInput }),
        })
        .then(async (response) => {
            if (!response.ok) {
                let errorMsg = `Server error: ${response.status}`;
                try {
                    const errData = await response.json();
                    // Use the specific error from backend if available
                    errorMsg = errData.error || `Server error: ${response.status} ${response.statusText}`;
                } catch (e) {
                    // If parsing fails, use the status text
                    errorMsg = `Server error: ${response.status} ${response.statusText}`;
                    console.warn("Could not parse error response body:", e);
                }
                throw new Error(errorMsg);
            }
            return response.json();
        })
        .then((data) => {
            finalizeProgress(true);
  
            if (data.characters && data.characters.length > 0) {
                resultsContainer.style.display = "grid";
  
                data.characters.forEach(character => {
                    const cardLink = document.createElement("a");
                    cardLink.href = `/chat/${character.url_name}`;
                    cardLink.classList.add("character-card-link");
  
                    const card = document.createElement("div");
                    card.classList.add("character-card");
  
                    const imageContainer = document.createElement("div");
                    imageContainer.classList.add("image-container");
  
                    const imgBg = document.createElement("img");
                    imgBg.classList.add("image-bg");
                    imgBg.src = `data:image/jpeg;base64,${character.image_data}`;
                    imgBg.alt = ""; // Decorative
  
                    const imgFg = document.createElement("img");
                    imgFg.classList.add("image-fg");
                    imgFg.src = `data:image/jpeg;base64,${character.image_data}`;
                    imgFg.alt = `Image of ${character.name}`;
  
                    // --- Enhanced Error Handling for Images ---
                    let fgError = false;
                    let bgError = false;
  
                    const handleImageError = () => {
                        if (fgError && bgError) { // Only add placeholder if BOTH fail
                             imageContainer.innerHTML = ''; // Clear potentially broken img tags
                             imageContainer.style.backgroundColor = 'var(--input-bg)'; // Darker fallback bg
                             const placeholderText = document.createElement('span');
                             placeholderText.textContent = 'Image unavailable';
                             placeholderText.style.cssText = `
                                 display: flex;
                                 align-items: center;
                                 justify-content: center;
                                 height: 100%;
                                 width: 100%; /* Ensure it spans */
                                 color: var(--text-color);
                                 font-size: 0.9em;
                                 opacity: 0.7;
                                 text-align: center;
                                 position: absolute; /* Position inside container */
                                 top: 0; left: 0;
                             `;
                             imageContainer.appendChild(placeholderText);
                        }
                    };
  
                    imgFg.onerror = () => {
                        imgFg.style.display = 'none'; // Hide broken foreground
                        fgError = true;
                        handleImageError();
                    };
                     imgBg.onerror = () => {
                        imgBg.style.display = 'none'; // Hide broken background
                        bgError = true;
                        handleImageError();
                    };
                    // --- End Enhanced Error Handling ---
  
  
                    imageContainer.appendChild(imgBg);
                    imageContainer.appendChild(imgFg);
  
                    const name = document.createElement("p");
                    name.classList.add("character-name");
                    name.textContent = character.name;
  
                    card.appendChild(imageContainer);
                    card.appendChild(name);
                    cardLink.appendChild(card);
                    resultsContainer.appendChild(cardLink);
                });
            } else if (data.error) {
                // Display error from backend response
                errorMessage.innerText = data.error;
                resultsContainer.style.display = "none";
                finalizeProgress(false); // Ensure progress stops cleanly on backend error
            } else {
                // Handle case where backend returns success but no characters
                errorMessage.innerText = "No matching character suggestions found. Try refining your traits.";
                resultsContainer.style.display = "none";
            }
        })
        .catch((error) => {
            console.error("Fetch Error:", error);
            finalizeProgress(false);
            // Display the error message thrown from the .then block or fetch itself
            errorMessage.innerText = error.message || "An unexpected network error occurred. Please try again.";
            resultsContainer.style.display = "none";
        });
    });
  });