// Script for prompt.html

const styleDescriptionInput = document.getElementById('style-description-input');
const submitButton = document.getElementById('submit-button');
const saveStatus = document.getElementById('save-status');

// Endpoint for automatic submission.
// Replace YOUR_FORM_ID with the ID from your Formspree form.
const SUBMIT_ENDPOINT = 'https://formspree.io/f/YOUR_FORM_ID';

function buildOutputData() {
    const feedbackData = JSON.parse(localStorage.getItem('imageFeedback')) || {};
    const styleDescription = styleDescriptionInput.value.trim();

    const formattedPreferences = [];
    const filenamePattern = /^images\/alg-([a-zA-Z0-9]+)_episode_(\d+)_timestep_(\d+)\.png$/i;

    for (const filename in feedbackData) {
        if (Object.prototype.hasOwnProperty.call(feedbackData, filename)) {
            const match = filename.match(filenamePattern);
            if (match) {
                formattedPreferences.push({
                    filename,
                    algorithm: match[1],
                    episode: parseInt(match[2], 10),
                    timestep: parseInt(match[3], 10),
                    preference: feedbackData[filename]
                });
            } else {
                // include raw if unexpected filename
                formattedPreferences.push({ filename, preference: feedbackData[filename] });
            }
        }
    }

    formattedPreferences.sort((a, b) => {
        if (a.algorithm !== b.algorithm) return String(a.algorithm).localeCompare(String(b.algorithm));
        if (a.episode !== b.episode) return (a.episode || 0) - (b.episode || 0);
        return (a.timestep || 0) - (b.timestep || 0);
    });

    const benchmarkEpisodeKeys = JSON.parse(localStorage.getItem('benchmarkEpisodeKeys')) || [];

    return {
        style_description: styleDescription,
        preferences: formattedPreferences,
        benchmark_episode_keys: benchmarkEpisodeKeys
    };
}

async function submitFeedback() {
    const feedbackData = JSON.parse(localStorage.getItem('imageFeedback')) || {};
    const styleDescription = styleDescriptionInput.value.trim();

    if (styleDescription === '') {
        alert("Please describe the style you had in mind before submitting.");
        return;
    }

    if (Object.keys(feedbackData).length === 0) {
        if (!confirm("Warning: No image preferences were found. This usually means the feedback steps were skipped.\n\nDo you want to submit anyway?")) {
            return;
        }
    }

    const outputData = buildOutputData();
    saveStatus.style.display = 'block';
    saveStatus.textContent = 'Submitting...';

    try {
        const response = await fetch(SUBMIT_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(outputData)
        });
        if (response.ok) {
            saveStatus.textContent = 'Submission successful. Thank you!';
            submitButton.disabled = true;
            // Clear stored data to maintain privacy
            localStorage.removeItem('imageFeedback');
            localStorage.removeItem('benchmarkEpisodeKeys');
        } else {
            console.warn('Submission failed:', response.statusText);
            saveStatus.textContent = 'Submission failed. Please try again later.';
        }
    } catch (err) {
        console.error('Submission error:', err);
        saveStatus.textContent = 'Submission failed. Please try again later.';
    }
}

submitButton.addEventListener('click', submitFeedback);
