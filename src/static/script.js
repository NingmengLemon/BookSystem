document.getElementById('queryButton').addEventListener('click', searchItems);

document.getElementById('addButton').addEventListener('click', function () {
    document.getElementById('addModal').style.display = 'block';
});

document.getElementById('cancelAddButton').addEventListener('click', function () {
    document.getElementById('addModal').style.display = 'none';
});

function searchItems() {
    const searchWord = document.getElementById("queryInput").value.trim()
    const searchType = document.querySelector('input[name="qTypeChoice"]:checked').value
    let api = '/search';
    if (searchWord.length > 0) {
        api += `?${encodeURIComponent(searchType)}=${encodeURIComponent(searchWord)}`;
    }
    fetch(api)
        .then(response => {
            if (!response.ok) {
                throw new Error('Response is not OK');
            }
            return response.json();
        })
        .then(data => {
            populateTable(data);
        })
        .catch(error => {
            alert('获取数据失败: ' + error.message);
        });
}

function populateTable(items) {
    const tbody = document.getElementById('itemsTable').getElementsByTagName('tbody')[0];
    tbody.innerHTML = ''; // 清空现有内容

    items.forEach(item => {
        const row = tbody.insertRow();

        // 插入各个单元格
        row.insertCell().innerText = item.id;
        row.insertCell().innerText = item.title;
        row.insertCell().innerText = item.isbn;
        row.insertCell().innerText = item.author;
        row.insertCell().innerText = item.publisher;
        row.insertCell().innerText = item.desc;

        // 封面
        const coverCell = row.insertCell();
        const img = document.createElement('img');
        img.src = item.cover;
        img.alt = 'cover';
        img.width = 50; // 调整图片大小
        coverCell.appendChild(img);

        row.insertCell().innerText = item.price.toFixed(2);
        row.insertCell().innerText = item.extra;

        // 操作按钮
        const actionCell = row.insertCell();

        // // 修改按钮
        // const modifyButton = document.createElement('button');
        // modifyButton.innerText = '修改';
        // modifyButton.addEventListener('click', () => modifyItem(item));
        // actionCell.appendChild(modifyButton);
        // 删除按钮
        const deleteButton = document.createElement('button');
        deleteButton.innerText = '删除';
        deleteButton.style.marginLeft = '10px';
        deleteButton.addEventListener('click', () => deleteItem(item.id));
        actionCell.appendChild(deleteButton);
    });
}

function deleteItem(id) {
    if (!confirm('确定要删除这个条目吗？')) {
        return;
    }
    fetch("/delete", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(id),
    })
        .then((response) => response.json())
        .then((data) => {
            console.log("Success:", data);
            searchItems();
        })
        .catch((error) => {
            console.error("Error:", error);
        });
}

document.getElementById('confirmAddButton').addEventListener('click', function () {
    const newEntry = {
        title: document.getElementById('title').value,
        isbn: document.getElementById('isbn').value,
        author: document.getElementById('author').value,
        publisher: document.getElementById('publisher').value,
        desc: document.getElementById('desc').value,
        cover: document.getElementById('cover').value,
        price: parseFloat(document.getElementById('price').value),
        extra: document.getElementById('extra').value
    };

    fetch('/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(newEntry)
    })
        .then(response => {
            if (response.ok) {
                alert('条目已成功添加');
                document.getElementById('addModal').style.display = 'none'; // 关闭弹窗
                searchItems()
            } else {
                alert('添加条目失败');
            }
        })
        .catch(error => {
            console.error('添加条目时出错:', error);
        });
});

// 自动加载数据
window.onload = searchItems;