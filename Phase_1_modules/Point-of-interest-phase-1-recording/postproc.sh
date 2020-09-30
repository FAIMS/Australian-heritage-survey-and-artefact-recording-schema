#!/usr/bin/env bash

cd module

string="
        <select1 appearance=\"compact\" ref=\"Entity_List\">
          <label>\{Entity_List\}<\/label>
          <item>
            <label>Options not loaded<\/label>
            <value>Options not loaded<\/value>
          <\/item>
        <\/select1>"
replacement="
        <group ref=\"Colgroup_1\" faims_style=\"orientation\">
          <label\/>
          <group ref=\"Col_1\" faims_style=\"even\">
            <label\/>
            <select1 ref=\"Select_Author\">
              <label>{Select_Author}<\/label>
              <item>
                <label>Options not loaded<\/label>
                <value>Options not loaded<\/value>
              <\/item>
            <\/select1>
          <\/group>
          <group ref=\"Col_2\" faims_style=\"even\">
            <label\/>
            <select1 ref=\"Select_Date\">
              <label>{Select_Date}<\/label>
              <item>
                <label>Options not loaded<\/label>
                <value>Options not loaded<\/value>
              <\/item>
            <\/select1>
          <\/group>
        <\/group>
        <select1 appearance=\"compact\" ref=\"Entity_List\">
          <label>{Entity_List}<\/label>
          <item>
            <label>Options not loaded<\/label>
            <value>Options not loaded<\/value>
          <\/item>
        <\/select1>"
perl -0777 -i.original -pe "s/$string/$replacement/igs" ui_schema.xml

string="
              <Entity_List\/>"
replacement="
              <Colgroup_1>
                <Col_1>
                  <Select_Author\/>
                <\/Col_1>
                <Col_2>
                  <Select_Date\/>
                <\/Col_2>
              <\/Colgroup_1>
              <Entity_List\/>"
perl -0777 -i.original -pe "s/$string/$replacement/igs" ui_schema.xml

string="
        <trigger ref=\"Center_Me_1\">
          <label>\{Center_Me}<\/label>
        <\/trigger>
        <trigger ref=\"Create_Shape\">
          <label>\{Create_Shape}<\/label>
        <\/trigger>"
replacement="
        <group ref=\"Colgroup_1\" faims_style=\"orientation\">
          <label\/>
          <group ref=\"Col_1\" faims_style=\"even\">
            <label\/>
            <trigger ref=\"Center_Me_1\">
            <label>{Center_Me}<\/label>
            <\/trigger>
          <\/group>
          <group ref=\"Col_2\" faims_style=\"even\">
            <label\/>
            <trigger ref=\"Create_Shape\">
              <label>{Create_Shape}<\/label>
            <\/trigger>
          <\/group>
        <\/group>"
perl -0777 -i.original -pe "s/$string/$replacement/igs" ui_schema.xml

string="
              <Center_Me_1\/>
              <Create_Shape\/>"
replacement="
              <Colgroup_1>
                <Col_1>
                  <Center_Me_1\/>
                <\/Col_1>
                <Col_2>
                  <Create_Shape\/>
                <\/Col_2>
              <\/Colgroup_1>"
perl -0777 -i.original -pe "s/$string/$replacement/igs" ui_schema.xml

string="
              <Center_Me_1\/>
              <Create_Shape\/>"
replacement="
              <Colgroup_1>
                <Col_1>
                  <Center_Me_1\/>
                <\/Col_1>
                <Col_2>
                  <Create_Shape\/>
                <\/Col_2>
              <\/Colgroup_1>"
perl -0777 -i.original -pe "s/$string/$replacement/igs" ui_schema.xml


string="
        <trigger ref=\"Center_Me_1\">
          <label>\{Center_Me}<\/label>
        <\/trigger>
        <trigger ref=\"Create_Shape\">
          <label>\{Create_Shape}<\/label>
        <\/trigger>"
replacement="
        <group ref=\"Colgroup_1\" faims_style=\"orientation\">
          <label\/>
          <group ref=\"Col_1\" faims_style=\"even\">
            <label\/>
            <trigger ref=\"Center_Me_1\">
            <label>{Center_Me}<\/label>
            <\/trigger>
          <\/group>
          <group ref=\"Col_2\" faims_style=\"even\">
            <label\/>
            <trigger ref=\"Create_Shape\">
              <label>{Create_Shape}<\/label>
            <\/trigger>
          <\/group>
        <\/group>"
perl -0777 -i.original -pe "s/$string/$replacement/igs" ui_schema.xml

string="<input faims_attribute_name=\"Mound ID\" faims_attribute_type=\"measure\" ref=\"Mound_ID\" faims_style_class=\"required\">"

replacement="<input faims_attribute_name=\"Mound ID\" faims_attribute_type=\"measure\" ref=\"Mound_ID\" faims_style_class=\"moundID\">"
perl -0777 -i.original -pe "s/$string/$replacement/igs" ui_schema.xml

sed -i -e "s/ mm$/ (mm)/" english.0.properties
sed -i -e "s/ m$/ (m)/" english.0.properties
sed -i -e "s/ m2$/ (m^2)/" english.0.properties
sed -i -e "s/ g$/ (g)/" english.0.properties
cat << EOF >> english.0.properties
Select_Author=Select Author
Select_Date=Select Date
Select_User=Select User
EOF

cat << EOF >> ui_styling.css
.moundID {
  color: #B2B2B2;
}
.moundID-label {
  color: red;
}
EOF

rm ui_schema.xml.original
