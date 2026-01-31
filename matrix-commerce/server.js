const express = require('express');
const bodyParser = require('body-parser');
const sdk = require('matrix-js-sdk');

const app = express();
const port = 3000;

// Middleware
app.use(bodyParser.json());
app.use(express.static('public'));

// Serve the main page
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Matrix Commerce</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 30px; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
        .product-card { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
      </style>
    </head>
    <body>
      <div class="container">
        <header>
          <h1>Matrix Commerce</h1>
          <p>Secure shopping through Matrix protocol</p>
        </header>
        
        <section>
          <h2>Products</h2>
          <div class="product-grid">
            <div class="product-card">
              <h3>Product 1</h3>
              <p>Description of product 1</p>
              <p><strong>$19.99</strong></p>
              <button onclick="addToCart('Product 1')">Add to Cart</button>
            </div>
            <div class="product-card">
              <h3>Product 2</h3>
              <p>Description of product 2</p>
              <p><strong>$29.99</strong></p>
              <button onclick="addToCart('Product 2')">Add to Cart</button>
            </div>
            <div class="product-card">
              <h3>Product 3</h3>
              <p>Description of product 3</p>
              <p><strong>$39.99</strong></p>
              <button onclick="addToCart('Product 3')">Add to Cart</button>
            </div>
          </div>
        </section>
        
        <section id="cart" style="margin-top: 30px;">
          <h2>Your Cart</h2>
          <div id="cart-items">Empty</div>
          <button onclick="checkout()">Checkout</button>
        </section>
      </div>
      
      <script>
        let cart = [];
        
        function addToCart(productName) {
          cart.push({name: productName, price: Math.floor(Math.random() * 50) + 10});
          updateCartDisplay();
        }
        
        function updateCartDisplay() {
          const cartItems = document.getElementById('cart-items');
          if (cart.length === 0) {
            cartItems.innerHTML = 'Empty';
            return;
          }
          
          cartItems.innerHTML = '<ul>' + 
            cart.map(item => '<li>' + item.name + ' - $' + item.price + '</li>').join('') + 
            '</ul>';
        }
        
        function checkout() {
          alert('Proceeding to secure checkout via Matrix protocol');
          // In a real implementation, this would connect to Matrix for secure payment processing
        }
      </script>
    </body>
    </html>
  `);
});

// API endpoint for payment processing
app.post('/api/process-payment', (req, res) => {
  const { amount, currency, userId } = req.body;
  
  console.log(`Processing payment: ${amount} ${currency} for user ${userId}`);
  
  // Simulate payment processing
  setTimeout(() => {
    res.json({
      success: true,
      transactionId: Math.random().toString(36).substring(2, 15),
      message: 'Payment processed successfully via Matrix protocol'
    });
  }, 1000);
});

app.listen(port, () => {
  console.log(`Matrix Commerce server running at http://localhost:${port}`);
});