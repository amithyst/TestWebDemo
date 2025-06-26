document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.color-widget-container').forEach(container => {
        const hiddenInput = container.querySelector('input[type="hidden"]');
        const palette = container.querySelector('.color-palette');
        const addBtn = container.querySelector('.add-color-btn');
        const colorPicker = container.querySelector('.color-picker-input');
        const randomCb = container.querySelector('.random-cb');

        function updateHiddenInput() {
            if (randomCb.checked) {
                hiddenInput.value = 'random';
                palette.style.display = 'none';
                return;
            }
            palette.style.display = 'flex';
            const colorDivs = palette.querySelectorAll('.color-display');
            const colors = Array.from(colorDivs).map(div => {
                // 将 hex (#RRGGBB) 转换为整数
                return parseInt(div.dataset.hex.substring(1), 16);
            });
            hiddenInput.value = JSON.stringify(colors);
        }

        addBtn.addEventListener('click', () => {
            const hex = colorPicker.value;
            const newColorDiv = document.createElement('div');
            newColorDiv.className = 'color-display';
            newColorDiv.style.backgroundColor = hex;
            newColorDiv.dataset.hex = hex;
            newColorDiv.innerHTML = '<span class="delete-color">&times;</span>';
            palette.appendChild(newColorDiv);
            updateHiddenInput();
        });

        palette.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-color')) {
                e.target.parentElement.remove();
                updateHiddenInput();
            }
        });

        randomCb.addEventListener('change', updateHiddenInput);

        // 初始化
        updateHiddenInput(); 
    });
});