const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.send('Hallo Josef');
});

app.listen(port, () => {
  console.log(`App läuft auf Port ${port}`);
});