document.addEventListener('DOMContentLoaded', (event) => {
    console.log('JavaScript is working!');

    let formsetContainer = document.getElementById('questions');
    let addQuestionBtn = document.getElementById('add-question-btn');
    let totalForms = document.querySelector('input[name="questions-TOTAL_FORMS"]');
    let emptyFormTemplate = document.getElementById('empty-form-template').innerHTML;

    if (formsetContainer && addQuestionBtn && totalForms) {
        addQuestionBtn.addEventListener('click', (e) => {
            e.preventDefault();
            let formCount = parseInt(totalForms.value);
            totalForms.value = formCount + 1;

            let newFormHtml = emptyFormTemplate.replace(/__prefix__/g, formCount);
            let newFormElement = document.createElement('div');
            newFormElement.innerHTML = newFormHtml;

            formsetContainer.appendChild(newFormElement);

            // Attach event listener for the delete button
            attachDeleteEvent(newFormElement);
            console.log('Added new form:', newFormHtml);
        });

        // Attach delete event listener to existing forms
        let existingForms = formsetContainer.querySelectorAll('.question-form');
        existingForms.forEach((form) => {
            attachDeleteEvent(form);
        });
    } else {
        console.error('Required elements not found in the DOM.');
    }
});

function attachDeleteEvent(formElement) {
    let deleteBtn = formElement.querySelector('.delete-question-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            formElement.remove();
            let totalForms = document.querySelector('input[name="questions-TOTAL_FORMS"]');
            totalForms.value = parseInt(totalForms.value) - 1;
        });
    }
}
