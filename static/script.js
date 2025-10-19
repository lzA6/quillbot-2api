document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const apiKeyInput = document.getElementById('api-key');
    const promptInput = document.getElementById('prompt-input');
    const generateBtn = document.getElementById('generate-btn');
    const ratioGroup = document.getElementById('ratio-group');
    const countSlider = document.getElementById('count-slider');
    const countValue = document.getElementById('count-value');
    const imageGrid = document.getElementById('image-grid');
    const spinner = document.getElementById('spinner');
    const errorMessage = document.getElementById('error-message');
    const placeholder = document.getElementById('placeholder');

    async function handleGenerate() {
        const apiKey = apiKeyInput.value.trim();
        const prompt = promptInput.value.trim();

        if (!apiKey || !prompt) {
            showError("请确保 API Key 和提示词都已填写。");
            return;
        }

        setLoading(true);

        const payload = {
            model: "quillbot-image-default",
            prompt: prompt,
            n: parseInt(countSlider.value, 10),
            size: ratioGroup.querySelector('.active').dataset.size,
        };

        try {
            const response = await fetch('/v1/images/generations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || '生成失败，未知错误。');
            }

            if (result.data && result.data.length > 0) {
                displayImages(result.data);
            } else {
                throw new Error('API 返回了成功状态，但没有图片数据。');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function displayImages(data) {
        imageGrid.innerHTML = '';
        data.forEach(item => {
            if (item.url) {
                const imgContainer = document.createElement('div');
                imgContainer.className = 'image-container';
                const img = document.createElement('img');
                img.src = item.url;
                img.alt = 'Generated Image';
                imgContainer.appendChild(img);
                imageGrid.appendChild(imgContainer);
            }
        });
    }

    function setLoading(isLoading) {
        generateBtn.disabled = isLoading;
        spinner.classList.toggle('hidden', !isLoading);
        placeholder.classList.toggle('hidden', isLoading || imageGrid.children.length > 0);
        if (isLoading) {
            imageGrid.innerHTML = '';
            hideError();
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
        imageGrid.innerHTML = '';
        placeholder.classList.add('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    // --- Event Listeners ---
    generateBtn.addEventListener('click', handleGenerate);
    countSlider.addEventListener('input', () => countValue.textContent = countSlider.value);
    ratioGroup.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            ratioGroup.querySelector('.active')?.classList.remove('active');
            e.target.classList.add('active');
        }
    });
});
