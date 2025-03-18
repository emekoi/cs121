/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-11.7.2-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: finalprojectdb
-- ------------------------------------------------------
-- Server version	11.7.2-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Current Database: `finalprojectdb`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `finalprojectdb` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `finalprojectdb`;

--
-- Table structure for table `albums`
--

DROP TABLE IF EXISTS `albums`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `albums` (
  `mbid` char(36) NOT NULL,
  `artist` char(36) NOT NULL,
  PRIMARY KEY (`mbid`,`artist`),
  KEY `artist` (`artist`),
  CONSTRAINT `albums_ibfk_1` FOREIGN KEY (`mbid`) REFERENCES `mbids` (`mbid`) ON DELETE CASCADE,
  CONSTRAINT `albums_ibfk_2` FOREIGN KEY (`artist`) REFERENCES `artists` (`mbid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `albums`
--

LOCK TABLES `albums` WRITE;
/*!40000 ALTER TABLE `albums` DISABLE KEYS */;
/*!40000 ALTER TABLE `albums` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `artists`
--

DROP TABLE IF EXISTS `artists`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `artists` (
  `mbid` char(36) NOT NULL,
  PRIMARY KEY (`mbid`),
  CONSTRAINT `artists_ibfk_1` FOREIGN KEY (`mbid`) REFERENCES `mbids` (`mbid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `artists`
--

LOCK TABLES `artists` WRITE;
/*!40000 ALTER TABLE `artists` DISABLE KEYS */;
/*!40000 ALTER TABLE `artists` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Temporary table structure for view `display_albums`
--

DROP TABLE IF EXISTS `display_albums`;
/*!50001 DROP VIEW IF EXISTS `display_albums`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `display_albums` AS SELECT
 1 AS `album`,
  1 AS `album_name`,
  1 AS `artist`,
  1 AS `artist_name` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `display_artists`
--

DROP TABLE IF EXISTS `display_artists`;
/*!50001 DROP VIEW IF EXISTS `display_artists`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `display_artists` AS SELECT
 1 AS `artist`,
  1 AS `artist_name` */;
SET character_set_client = @saved_cs_client;

--
-- Temporary table structure for view `display_tracks`
--

DROP TABLE IF EXISTS `display_tracks`;
/*!50001 DROP VIEW IF EXISTS `display_tracks`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `display_tracks` AS SELECT
 1 AS `track`,
  1 AS `track_name`,
  1 AS `album`,
  1 AS `album_name`,
  1 AS `artist`,
  1 AS `artist_name`,
  1 AS `track_length` */;
SET character_set_client = @saved_cs_client;

--
-- Table structure for table `genres`
--

DROP TABLE IF EXISTS `genres`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `genres` (
  `mbid` char(36) NOT NULL,
  `genre_name` varchar(32) NOT NULL,
  PRIMARY KEY (`mbid`,`genre_name`),
  CONSTRAINT `genres_ibfk_1` FOREIGN KEY (`mbid`) REFERENCES `mbids` (`mbid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `genres`
--

LOCK TABLES `genres` WRITE;
/*!40000 ALTER TABLE `genres` DISABLE KEYS */;
/*!40000 ALTER TABLE `genres` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mbids`
--

DROP TABLE IF EXISTS `mbids`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `mbids` (
  `mbid` char(36) NOT NULL,
  `mbid_name` varchar(256) NOT NULL,
  `mbid_type` enum('artist','album','track') NOT NULL,
  PRIMARY KEY (`mbid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mbids`
--

LOCK TABLES `mbids` WRITE;
/*!40000 ALTER TABLE `mbids` DISABLE KEYS */;
/*!40000 ALTER TABLE `mbids` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `scores`
--

DROP TABLE IF EXISTS `scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `scores` (
  `user_name` varchar(16) NOT NULL,
  `mbid` char(36) NOT NULL,
  `last_access` int(11) NOT NULL,
  `last_crf` double NOT NULL,
  PRIMARY KEY (`user_name`,`mbid`),
  KEY `mbid` (`mbid`),
  CONSTRAINT `scores_ibfk_1` FOREIGN KEY (`mbid`) REFERENCES `mbids` (`mbid`) ON DELETE CASCADE,
  CONSTRAINT `scores_ibfk_2` FOREIGN KEY (`user_name`) REFERENCES `users` (`user_name`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `scores`
--

LOCK TABLES `scores` WRITE;
/*!40000 ALTER TABLE `scores` DISABLE KEYS */;
/*!40000 ALTER TABLE `scores` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `scrobbles`
--

DROP TABLE IF EXISTS `scrobbles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `scrobbles` (
  `scrobble_id` int(11) NOT NULL AUTO_INCREMENT,
  `scrobble_time` int(11) NOT NULL,
  `mbid` char(36) NOT NULL,
  `user_name` varchar(16) NOT NULL,
  PRIMARY KEY (`scrobble_id`),
  KEY `mbid` (`mbid`),
  KEY `user_name` (`user_name`),
  CONSTRAINT `scrobbles_ibfk_1` FOREIGN KEY (`mbid`) REFERENCES `tracks` (`mbid`) ON DELETE CASCADE,
  CONSTRAINT `scrobbles_ibfk_2` FOREIGN KEY (`user_name`) REFERENCES `users` (`user_name`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `scrobbles`
--

LOCK TABLES `scrobbles` WRITE;
/*!40000 ALTER TABLE `scrobbles` DISABLE KEYS */;
/*!40000 ALTER TABLE `scrobbles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tracks`
--

DROP TABLE IF EXISTS `tracks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tracks` (
  `mbid` char(36) NOT NULL,
  `artist` char(36) NOT NULL,
  `album` char(36) DEFAULT NULL,
  `length` time NOT NULL,
  PRIMARY KEY (`mbid`,`artist`),
  KEY `album` (`album`),
  KEY `artist` (`artist`),
  CONSTRAINT `tracks_ibfk_1` FOREIGN KEY (`mbid`) REFERENCES `mbids` (`mbid`) ON DELETE CASCADE,
  CONSTRAINT `tracks_ibfk_2` FOREIGN KEY (`album`) REFERENCES `albums` (`mbid`) ON DELETE CASCADE,
  CONSTRAINT `tracks_ibfk_3` FOREIGN KEY (`artist`) REFERENCES `artists` (`mbid`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tracks`
--

LOCK TABLES `tracks` WRITE;
/*!40000 ALTER TABLE `tracks` DISABLE KEYS */;
/*!40000 ALTER TABLE `tracks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_name` varchar(64) NOT NULL,
  `user_salt` char(8) NOT NULL,
  `user_hash` binary(64) NOT NULL,
  `user_admin` tinyint(4) NOT NULL,
  `user_session` binary(32) DEFAULT NULL,
  `user_last_update` int(11) DEFAULT NULL,
  PRIMARY KEY (`user_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES
('emekoi','!q8dny9O','2436a5b52309ff7a46bfd7da4532d62d011196e0b14002afc25745395823b502',0,'v9QfbotxVCCXydyw_wHouadkPVtWm6YW',0);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Current Database: `finalprojectdb`
--

USE `finalprojectdb`;

--
-- Final view structure for view `display_albums`
--

/*!50001 DROP VIEW IF EXISTS `display_albums`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `display_albums` AS select `albums`.`mbid` AS `album`,`mbids`.`mbid_name` AS `album_name`,`display_artists`.`artist` AS `artist`,`display_artists`.`artist_name` AS `artist_name` from ((`albums` join `mbids` on(`albums`.`mbid` = `mbids`.`mbid`)) join `display_artists` on(`albums`.`artist` = `display_artists`.`artist`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `display_artists`
--

/*!50001 DROP VIEW IF EXISTS `display_artists`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `display_artists` AS select `artists`.`mbid` AS `artist`,`mbids`.`mbid_name` AS `artist_name` from (`artists` join `mbids` on(`artists`.`mbid` = `mbids`.`mbid`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `display_tracks`
--

/*!50001 DROP VIEW IF EXISTS `display_tracks`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_uca1400_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `display_tracks` AS select `tracks`.`mbid` AS `track`,`mbids`.`mbid_name` AS `track_name`,`display_albums`.`album` AS `album`,`display_albums`.`album_name` AS `album_name`,`display_artists`.`artist` AS `artist`,`display_artists`.`artist_name` AS `artist_name`,`tracks`.`length` AS `track_length` from (((`tracks` join `mbids` on(`tracks`.`mbid` = `mbids`.`mbid`)) join `display_artists` on(`tracks`.`artist` = `display_artists`.`artist`)) left join `display_albums` on(`tracks`.`album` = `display_albums`.`album`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2025-03-18  3:39:40
