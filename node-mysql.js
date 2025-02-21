/**
 * Example of connecting to MySQL DB from another application
 * (here, we use Node.js, but Python is another popular choice).
 *
 * Note: This is just extra material to see queries and stored routines used outside of MySQL.
 * No need to learn Node.js :)
 */
const mysql = require("mysql");

// Define the credentials for the database connection
const connection = mysql.createConnection({
  host: "localhost",
  port: "8889", // you can find the port in phpMyAdmin or your mysql config
  user: "airbnbadmin",
  password: "adminpw",
  // user: "airbnbclient",
  // password: "clientpw",
  database: "airbnbdb"
});

// Once we set up the connection with required credentials, we try to connect so we
// can query on the connected object.
connection.connect(function(err) {
  if (err) {
    throw err;
  }
  console.log("Connected!");
});

let hostName = "Kia";
// This query _will_ work for both users (both have SELECT privileges)
let kiasRows;
// query functions are asynchronous, so you'll see this higher-order 'callback'
// function structure often
connection.query(`SELECT * FROM hosts WHERE host_name LIKE '${hostName}'`, 
  function(err, rows) {
    if (err) {
      console.log("Error: " + err);
    } else {
      kiasRows = rows;
      console.log(rows);
    }
});

// Will work for airbnbadmin, not airbnbclient due to
// granted privileges (client only has SELECT privileges)
connection.query("CALL superhosts()", function(err, rows) {
  if (err) {
    console.log(err);
  } else {
    // First result
    console.log(rows[0]);
  }
});

// An example motivating using a procedure to support inserting new hosts in some application.
// You can imagine getting other variables from a web interface before calling a procedure.
// Again, will work for airbnbadmin, not airbnbclient due to
// granted privileges (client only has SELECT privileges)
hostName = "Lorem";
connection.query(`CALL add_host2(121, '${hostName}', NOW(), 1);`, 
  function(err, rows) {
    if (err) {
       console.log(`Could not add ${hostName} to database.`);
       console.log(err);
    } else {
      console.log(`${hostName} added successfully to database!`);
      console.log(rows);
    }
});
